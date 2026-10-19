"""Run the real batch workflow at 1, 5, and twice at 20 images."""

from __future__ import annotations

import json
import argparse
import time
from collections import Counter
from io import BytesIO

from PIL import Image

from image_workflow import ImageInput, process_batch


def error_type(message: str) -> str:
    if "429" in message:
        return "rate_limit_429"
    if "timed out" in message.lower() or "超过 20 秒" in message:
        return "timeout"
    if "10013" in message:
        return "network_permission"
    return "other"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, choices=(1, 5, 20))
    parser.add_argument("--repeat", type=int, default=1)
    args = parser.parse_args()
    buffer = BytesIO()
    Image.new("RGB", (120, 160), "#728b64").save(buffer, "JPEG")
    sizes = (args.size,) * args.repeat if args.size else (1, 5, 20, 20)
    for size in sizes:
        items = [ImageInput(f"sample-{index}.jpg", buffer.getvalue())
                 for index in range(size)]
        started = time.monotonic()
        result = process_batch(items, text_detector=lambda _: True)
        print(json.dumps({
            "size": size,
            "batch_seconds": round(time.monotonic() - started, 3),
            "successful_outputs": len(result.successful),
            "failed_outputs": len(result.failed),
            "online_uses": result.photo_fetch_stats["online_uses"],
            "backup_uses": result.photo_fetch_stats["backup_uses"],
            "first_photo_seconds": result.photo_fetch_stats["first_photo_seconds"],
            "searches": result.photo_fetch_stats["searches"],
            "download_attempts": result.photo_fetch_stats["download_attempts"],
            "error_types": dict(Counter(error_type(error)
                                        for error in result.photo_fetch_stats["errors"])),
        }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
