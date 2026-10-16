"""Seven-stage, in-memory image processing workflow."""

from __future__ import annotations

import random
import re
import secrets
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Callable, Sequence

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from .ocr import detect_text
from .stickers import PhotoOverlay, bundled_photo, random_photo

OUTPUT_SIZE = (1280, 1706)
MAX_BATCH = 20
STAGES = ("geometry", "color", "text", "sticker", "graffiti", "composite", "export")
TextDetector = Callable[[Image.Image], bool | None]
ProgressCallback = Callable[[int, int, str, str], None]


@dataclass(frozen=True)
class ImageInput:
    name: str
    data: bytes


@dataclass
class ImageResult:
    input_name: str
    output_name: str
    data: bytes | None = None
    error: str | None = None
    stage: str | None = None
    seconds: float = 0.0
    details: dict[str, object] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.data is not None


@dataclass
class BatchResult:
    images: list[ImageResult]
    sticker_source: str
    sticker_error: str | None = None

    @property
    def successful(self) -> list[ImageResult]:
        return [image for image in self.images if image.ok]

    @property
    def failed(self) -> list[ImageResult]:
        return [image for image in self.images if not image.ok]

    def to_zip(self) -> bytes:
        """Export successful results; unsuccessful inputs have no ZIP entry."""
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for image in self.successful:
                archive.writestr(image.output_name, image.data)
        return buffer.getvalue()


def _open_image(data: bytes) -> Image.Image:
    if not data:
        raise ValueError("空文件")
    with Image.open(BytesIO(data)) as source:
        if source.format not in {"JPEG", "PNG", "WEBP"}:
            raise ValueError("仅支持 JPG、PNG、WebP")
        if source.width * source.height > 30_000_000:
            raise ValueError("图片像素过大（上限 3000 万像素）")
        image = ImageOps.exif_transpose(source)
        image.load()
        if image.mode == "RGBA":
            canvas = Image.new("RGBA", image.size, "white")
            return Image.alpha_composite(canvas, image).convert("RGB")
        return image.convert("RGB")


def _geometry(image: Image.Image, rng: random.Random, flip: bool) -> Image.Image:
    # Cropping after rotation removes exposed white corners and makes shifts real.
    width, height = image.size
    shifted = Image.new("RGB", image.size, "white")
    shifted.paste(image, (rng.randint(-8, 8), rng.randint(-8, 8)))
    rotated = shifted.rotate(
        rng.uniform(-1, 1), resample=Image.Resampling.BICUBIC,
        fillcolor="white",
    )
    inset = max(1, int(min(width, height) * 0.025))
    if width > 2 * inset and height > 2 * inset:
        rotated = rotated.crop((inset, inset, width - inset, height - inset))
    result = ImageOps.fit(rotated, OUTPUT_SIZE, Image.Resampling.LANCZOS)
    return ImageOps.mirror(result) if flip else result


def _color(image: Image.Image, rng: random.Random) -> tuple[Image.Image, dict[str, float]]:
    factors = {
        "brightness": rng.uniform(1, 1.04),
        "contrast": rng.uniform(0.96, 1.04),
        "saturation": rng.uniform(0.96, 1.04),
        "sharpness": rng.uniform(1, 1.08),
    }
    image = ImageEnhance.Brightness(image).enhance(factors["brightness"])
    image = ImageEnhance.Contrast(image).enhance(factors["contrast"])
    image = ImageEnhance.Color(image).enhance(factors["saturation"])
    image = ImageEnhance.Sharpness(image).enhance(factors["sharpness"])
    image = Image.blend(image, image.filter(ImageFilter.DETAIL), 0.01)
    return image, {key: round(value, 4) for key, value in factors.items()}


def _font() -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    candidates = (
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/msyh.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    )
    for path in candidates:
        if Path(path).is_file():
            try:
                return ImageFont.truetype(path, 24)
            except OSError:
                pass
    return ImageFont.load_default(24)


def _text_layer(size: tuple[int, int], rng: random.Random) -> Image.Image:
    layer = Image.new("RGBA", size)
    draw = ImageDraw.Draw(layer)
    phrase = rng.choice(("晨曦微风星光暖阳花香", "光影纹理色彩线条质感", "花瓣云朵雨滴晨光微风"))
    font = _font()
    for y in range(0, size[1], 80):
        for x in range(0, size[0], 100):
            shade = rng.randint(205, 250)
            draw.text((x + rng.randint(-8, 8), y + rng.randint(-8, 8)),
                      phrase, font=font, fill=(shade, shade, shade, 255))
    return layer


def _sticker_overlay(image: Image.Image, photo: PhotoOverlay, rng: random.Random) -> Image.Image:
    # A real photograph covers the complete canvas at exactly 1% blend strength.
    fitted = ImageOps.fit(photo.image, image.size, Image.Resampling.LANCZOS,
                          centering=(rng.random(), rng.random()))
    return Image.blend(image, fitted, 0.01)


def _graffiti(layer: Image.Image, rng: random.Random) -> None:
    draw = ImageDraw.Draw(layer)
    width, height = layer.size
    for _ in range(120):
        x, y = rng.randrange(width), rng.randrange(height)
        size = rng.randint(5, 90)
        color = (*[rng.randint(30, 225) for _ in range(3)], 255)
        shape = rng.randrange(4)
        if shape == 0:
            draw.line((x, y, x + size, y + rng.randint(-size, size)), fill=color, width=3)
        elif shape == 1:
            draw.ellipse((x, y, x + size, y + size), outline=color, width=3)
        elif shape == 2:
            draw.rectangle((x, y, x + size, y + size), outline=color, width=3)
        else:
            draw.arc((x, y, x + size, y + size), 0, 270, fill=color, width=3)


def _composite(base: Image.Image, layer: Image.Image) -> Image.Image:
    # 3/255 matches the legacy implementation's ~1.18% opacity.
    alpha = layer.getchannel("A").point(lambda value: 3 if value else 0)
    layer.putalpha(alpha)
    return Image.alpha_composite(base.convert("RGBA"), layer).convert("RGB")


def _output_name(name: str, index: int) -> str:
    stem = Path(name.replace("\\", "/")).stem
    stem = re.sub(r"[^\w\-]+", "_", stem, flags=re.UNICODE).strip("_")[:80] or "image"
    return f"{index + 1:02d}_{stem}_processed.png"


def process_image(
    item: ImageInput, *, index: int = 0, photo: PhotoOverlay | None = None,
    text_detector: TextDetector = detect_text, seed: int | None = None,
    progress: Callable[[str], None] | None = None,
) -> ImageResult:
    """Process one image; errors are returned with the stage where they occurred."""
    start = time.perf_counter()
    rng = random.Random(seed if seed is not None else secrets.randbits(64))
    photo = photo or bundled_photo(rng)
    result = ImageResult(item.name, _output_name(item.name, index))
    stage = "geometry"
    try:
        image = _open_image(item.data)
        try:
            has_text = text_detector(image)
        except Exception:
            has_text = None
        flip = has_text is False and rng.choice((True, False))
        result.details["text_detection"] = has_text
        result.details["flipped"] = flip
        for stage in STAGES:
            if progress:
                progress(stage)
            if stage == "geometry":
                image = _geometry(image, rng, flip)
            elif stage == "color":
                image, color_factors = _color(image, rng)
                result.details["color_factors"] = color_factors
            elif stage == "text":
                layer = _text_layer(image.size, rng)
            elif stage == "sticker":
                image = _sticker_overlay(image, photo, rng)
                result.details["photo_source"] = photo.source_url
                result.details["photo_provider"] = photo.source_name
                result.details["photo_search_term"] = photo.search_term
                result.details["photo_search_offset"] = photo.search_offset
                if photo.fallback_reason:
                    result.details["photo_fallback_reason"] = photo.fallback_reason
            elif stage == "graffiti":
                _graffiti(layer, rng)
            elif stage == "composite":
                image = _composite(image, layer)
                del layer
            elif stage == "export":
                output = BytesIO()
                image.save(output, format="PNG", optimize=True)
                result.data = output.getvalue()
        result.stage = "complete"
    except Exception as error:
        result.stage = stage
        result.error = str(error) or type(error).__name__
    finally:
        result.seconds = round(time.perf_counter() - start, 3)
    return result


def process_batch(
    items: Sequence[ImageInput], *, text_detector: TextDetector = detect_text,
    photo_loader: Callable[[random.Random], PhotoOverlay] = random_photo,
    seed: int | None = None, progress: ProgressCallback | None = None,
) -> BatchResult:
    """Process at most 20 uploads independently, preserving input order."""
    if not 1 <= len(items) <= MAX_BATCH:
        raise ValueError("每批需上传 1 至 20 张图片")
    batch_rng = random.Random(seed if seed is not None else secrets.randbits(64))
    image_seeds = [batch_rng.getrandbits(64) for _ in items]
    with ThreadPoolExecutor(max_workers=min(8, len(items))) as pool:
        futures = [pool.submit(photo_loader, random.Random(image_seed)) for image_seed in image_seeds]
        photos = []
        for image_seed, future in zip(image_seeds, futures):
            try:
                photos.append(future.result())
            except Exception as error:
                photos.append(bundled_photo(random.Random(image_seed), str(error)))
    results = []
    for index, (item, photo, image_seed) in enumerate(zip(items, photos, image_seeds)):
        notify = None
        if progress:
            notify = lambda stage, i=index, name=item.name: progress(i + 1, len(items), stage, name)
        results.append(process_image(
            item, index=index, photo=photo, text_detector=text_detector,
            seed=image_seed, progress=notify,
        ))
    source = "Wikimedia Commons" if all(p.source_name == "Wikimedia Commons" for p in photos) else "photo backup used"
    errors = [p.fallback_reason for p in photos if p.fallback_reason]
    return BatchResult(results, source, "; ".join(errors) if errors else None)
