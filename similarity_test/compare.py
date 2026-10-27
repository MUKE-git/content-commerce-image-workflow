"""Reproduce the attachment's four metrics and weighted duplicate rule locally.

These scores describe this test system only; they are not platform scores.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

try:
    import cv2
except ImportError:  # The bundled desktop Python can run the same calculation without OpenCV.
    cv2 = None

SIZE = 512
WEIGHTS = {"SSIM": 0.50, "PSNR": 0.30, "MSE": 0.10, "MAD": 0.10}


def _load(path: Path) -> tuple[np.ndarray, dict]:
    try:
        with Image.open(path) as source:
            source.verify()
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            width, height = image.size
            if width * height > 30_000_000:
                raise ValueError(f"图片超过 3000 万像素：{path}")
            # Preserve aspect ratio and use the same neutral canvas for both images.
            image.thumbnail((SIZE, SIZE), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (SIZE, SIZE), "white")
            canvas.paste(image, ((SIZE - image.width) // 2, (SIZE - image.height) // 2))
            return np.asarray(canvas, dtype=np.uint8), {
                "path": str(path.resolve()), "width": width, "height": height,
                "format": source.format,
            }
    except (OSError, UnidentifiedImageError) as exc:
        raise ValueError(f"无法读取图片：{path}") from exc


def _ssim(first: np.ndarray, second: np.ndarray) -> float:
    if cv2 is not None:
        x = cv2.cvtColor(first, cv2.COLOR_RGB2GRAY).astype(np.float64)
        y = cv2.cvtColor(second, cv2.COLOR_RGB2GRAY).astype(np.float64)
        blur = lambda array: cv2.GaussianBlur(array, (11, 11), 1.5)
    else:
        x = np.asarray(Image.fromarray(first).convert("L"), dtype=np.float64)
        y = np.asarray(Image.fromarray(second).convert("L"), dtype=np.float64)
        blur = _gaussian_blur
    mu_x = blur(x)
    mu_y = blur(y)
    var_x = blur(x * x) - mu_x * mu_x
    var_y = blur(y * y) - mu_y * mu_y
    cov = blur(x * y) - mu_x * mu_y
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    value = ((2 * mu_x * mu_y + c1) * (2 * cov + c2)) / (
        (mu_x * mu_x + mu_y * mu_y + c1) * (var_x + var_y + c2)
    )
    return float(np.clip(np.mean(value), -1, 1))


def _gaussian_blur(array: np.ndarray) -> np.ndarray:
    offsets = np.arange(-5, 6, dtype=np.float64)
    kernel = np.exp(-(offsets * offsets) / (2 * 1.5 * 1.5))
    kernel /= kernel.sum()
    padded = np.pad(array, ((5, 5), (0, 0)), mode="reflect")
    vertical = sum(kernel[i] * padded[i:i + array.shape[0], :] for i in range(11))
    padded = np.pad(vertical, ((0, 0), (5, 5)), mode="reflect")
    return sum(kernel[i] * padded[:, i:i + array.shape[1]] for i in range(11))


def _clamp(value: float) -> float:
    return min(100.0, max(0.0, value))


def compare(original: Path, candidate: Path) -> dict:
    a, original_info = _load(Path(original))
    b, candidate_info = _load(Path(candidate))
    delta = a.astype(np.float64) - b.astype(np.float64)
    mse = float(np.mean(delta * delta))
    mad = float(np.mean(np.abs(delta)))
    psnr = None if mse == 0 else float(20 * math.log10(255 / math.sqrt(mse)))
    ssim = _ssim(a, b)
    scores = {
        "SSIM": _clamp((ssim - 0.5) * 200),
        "PSNR": 100.0 if psnr is None else _clamp((psnr - 10) * 3),
        "MSE": _clamp((500 - mse) * 0.2),
        "MAD": _clamp((50 - mad) * 2),
    }
    total = sum(scores[key] * WEIGHTS[key] for key in WEIGHTS)
    if total >= 75:
        verdict = "重复"
    elif total >= 60:
        verdict = "疑似重复"
    else:
        verdict = "不重复"
    return {
        "system": "本地两图查重模拟系统",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "images": {"original": original_info, "candidate": candidate_info},
        "alignment": "EXIF 方向校正；等比例缩放至 512×512 白底居中画布",
        "metrics": {"SSIM": round(ssim, 6), "PSNR_dB": None if psnr is None else round(psnr, 4),
                    "MSE": round(mse, 4), "MAD": round(mad, 4)},
        "component_scores": {key: round(value, 2) for key, value in scores.items()},
        "similarity_score": round(total, 2),
        "verdict": verdict,
        "thresholds": {"duplicate": 75, "suspected_duplicate": 60},
        "weights": WEIGHTS,
        "limitations": "仅为附件规则的离线模拟；不能推断小红书、抖音或其他平台的实际审核结果。",
    }


def markdown_report(result: dict) -> str:
    m = result["metrics"]
    psnr = "∞（像素完全一致）" if m["PSNR_dB"] is None else f'{m["PSNR_dB"]:.4f} dB'
    return (
        "# 两图相似度测试报告\n\n"
        f'- 原图：`{result["images"]["original"]["path"]}`\n'
        f'- 待测图：`{result["images"]["candidate"]["path"]}`\n'
        f'- 对齐方式：{result["alignment"]}\n\n'
        "| 指标 | 数值 |\n| --- | ---: |\n"
        f'| SSIM | {m["SSIM"]:.6f} |\n| PSNR | {psnr} |\n'
        f'| MSE | {m["MSE"]:.4f} |\n| MAD | {m["MAD"]:.4f} |\n'
        f'| 综合相似分 | **{result["similarity_score"]:.2f}/100** |\n\n'
        f'**本系统判定：{result["verdict"]}**（≥75 重复，60–<75 疑似重复，<60 不重复）。\n\n'
        "## 模拟范围\n\n"
        "本工具模拟发布内容与已有图片的两图相似度检测。它使用附件中的四项指标、权重和阈值；"
        "真实社交平台可能还会使用感知特征、文字、视频、账号与行为等信号，内部规则未知。"
        "本报告不代表小红书、抖音等平台的审核结果。\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="本地两图相似度模拟测试")
    parser.add_argument("original", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--output", type=Path, help="报告目录；默认只打印结果")
    args = parser.parse_args()
    try:
        result = compare(args.original, args.candidate)
    except (ValueError, FileNotFoundError) as exc:
        parser.exit(2, f"测试失败：{exc}\n")
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        (args.output / "report.md").write_text(markdown_report(result), encoding="utf-8")
    print(markdown_report(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
