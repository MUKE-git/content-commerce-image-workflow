"""Fetch public-domain images for the low-opacity sticker layer."""

from __future__ import annotations

from io import BytesIO
from uuid import UUID

import requests
from PIL import Image

SEARCH_TERMS = ("leaves texture", "flowers texture", "paper texture", "stone texture")
MAX_DOWNLOAD_BYTES = 6 * 1024 * 1024
OPENVERSE_API = "https://api.openverse.org/v1/images/"


def fetch_openverse_stickers(query: str, limit: int = 4) -> list[Image.Image]:
    """Fetch up to ``limit`` CC0 or public-domain Openverse thumbnails."""
    try:
        response = requests.get(
            OPENVERSE_API,
            params={"q": query, "license": "cc0,pdm", "mature": "false", "page_size": max(8, limit * 2)},
            timeout=(5, 12),
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        stickers: list[Image.Image] = []
        for result in results:
            if result.get("license") not in {"cc0", "pdm"} or result.get("mature") is True:
                continue
            try:
                image_id = str(UUID(result["id"]))
            except (KeyError, ValueError, TypeError):
                continue
            # Build the URL ourselves so search results cannot choose a download host.
            url = f"{OPENVERSE_API}{image_id}/thumb/"
            image_response = None
            try:
                image_response = requests.get(url, timeout=(5, 12), stream=True)
                image_response.raise_for_status()
                content = bytearray()
                for chunk in image_response.iter_content(64 * 1024):
                    content.extend(chunk)
                    if len(content) > MAX_DOWNLOAD_BYTES:
                        raise ValueError("Openverse image exceeds download limit")
                with Image.open(BytesIO(content)) as image:
                    stickers.append(image.convert("RGB"))
            except (requests.RequestException, OSError, ValueError):
                continue
            finally:
                if image_response is not None:
                    image_response.close()
            if len(stickers) >= limit:
                break
        if not stickers:
            raise RuntimeError("Openverse 搜索无可用图片")
        return stickers
    except (requests.RequestException, ValueError, TypeError) as error:
        raise RuntimeError(f"Openverse 请求失败：{error}") from error
