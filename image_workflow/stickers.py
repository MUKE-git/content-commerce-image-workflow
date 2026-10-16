"""Fetch a small reusable batch of photos for the low-opacity sticker layer."""

from __future__ import annotations

import os
from io import BytesIO

import requests
from PIL import Image

SEARCH_TERMS = ("leaves texture", "flowers texture", "paper texture", "stone texture")
MAX_DOWNLOAD_BYTES = 6 * 1024 * 1024


def fetch_pexels_stickers(query: str, limit: int = 4) -> list[Image.Image]:
    """Fetch up to ``limit`` Pexels images; report why fallback is needed."""
    key = os.getenv("PEXELS_API_KEY")
    if not key:
        raise RuntimeError("未配置 PEXELS_API_KEY")
    try:
        response = requests.get(
            "https://api.pexels.com/v1/search",
            params={"query": query, "per_page": limit},
            headers={"Authorization": key}, timeout=(5, 12),
        )
        response.raise_for_status()
        photos = response.json().get("photos", [])
        stickers: list[Image.Image] = []
        for photo in photos:
            url = (photo.get("src") or {}).get("small")
            if not url or not url.startswith("https://images.pexels.com/"):
                continue
            image_response = None
            try:
                image_response = requests.get(url, timeout=(5, 12), stream=True)
                image_response.raise_for_status()
                content = bytearray()
                for chunk in image_response.iter_content(64 * 1024):
                    content.extend(chunk)
                    if len(content) > MAX_DOWNLOAD_BYTES:
                        raise ValueError("Pexels image exceeds download limit")
                with Image.open(BytesIO(content)) as image:
                    stickers.append(image.convert("RGB"))
            except (requests.RequestException, OSError, ValueError):
                continue
            finally:
                if image_response is not None:
                    image_response.close()
        if not stickers:
            raise RuntimeError("Pexels 搜索无可用图片")
        return stickers
    except (requests.RequestException, ValueError, TypeError) as error:
        raise RuntimeError(f"Pexels 请求失败：{error}") from error
