"""Find a random real photo for each image, with downloaded photo backups."""

from __future__ import annotations

import random
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
PHOTO_DIR = Path(__file__).resolve().parent.parent / "assets" / "overlay_photos"
SEARCH_TERMS = ("leaf texture", "paper texture", "stone texture", "flower petals texture")
MAX_DOWNLOAD_BYTES = 6 * 1024 * 1024
HEADERS = {"User-Agent": "ContentCommerceImageWorkflow/0.1 (portfolio project)"}
PEXELS_PAGES = {
    "paper": "https://www.pexels.com/photo/texture-of-crumpled-paper-4834961/",
    "leaves": "https://www.pexels.com/photo/texture-of-green-leaves-16730629/",
    "stone": "https://www.pexels.com/photo/close-up-of-stone-surface-texture-9348450/",
    "flower": "https://www.pexels.com/photo/closeup-of-a-pink-tulip-with-raindrops-on-petals-13833083/",
}


@dataclass
class PhotoOverlay:
    image: Image.Image
    source_url: str
    source_name: str
    search_term: str | None = None
    search_offset: int | None = None
    fallback_reason: str | None = None


def bundled_photo(rng: random.Random, reason: str | None = None) -> PhotoOverlay:
    """Choose one of the verified real photos when live search is unavailable."""
    name = rng.choice(tuple(PEXELS_PAGES))
    with Image.open(PHOTO_DIR / f"{name}.jpg") as image:
        return PhotoOverlay(image.convert("RGB"), PEXELS_PAGES[name], "Pexels backup",
                            fallback_reason=reason)


def _download_photo(url: str) -> Image.Image:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {"thumb.wikimedia.org", "upload.wikimedia.org"}:
        raise ValueError("图片下载地址不受信任")
    response = requests.get(url, headers=HEADERS, timeout=(3, 7), stream=True)
    try:
        response.raise_for_status()
        content = bytearray()
        for chunk in response.iter_content(64 * 1024):
            content.extend(chunk)
            if len(content) > MAX_DOWNLOAD_BYTES:
                raise ValueError("照片超过下载上限")
        with Image.open(BytesIO(content)) as image:
            if image.width * image.height > 30_000_000:
                raise ValueError("照片像素过大")
            return image.convert("RGB")
    finally:
        response.close()


def random_photo(rng: random.Random) -> PhotoOverlay:
    """Randomize the query and offset for every image; no usage list is kept."""
    term = rng.choice(SEARCH_TERMS)
    offset = rng.randrange(32)
    try:
        response = requests.get(
            COMMONS_API,
            params={
                "action": "query", "generator": "search", "gsrsearch": f"filetype:bitmap {term}",
                "gsrnamespace": 6, "gsroffset": offset, "gsrlimit": 8,
                "prop": "imageinfo", "iiprop": "url|mime", "iiurlwidth": 1280,
                "format": "json", "formatversion": 2,
            },
            headers=HEADERS, timeout=(3, 7),
        )
        response.raise_for_status()
        pages = response.json().get("query", {}).get("pages", [])
        candidates = []
        for page in pages:
            if not page.get("imageinfo"):
                continue
            info = page["imageinfo"][0]
            if info.get("mime") in {"image/jpeg", "image/png", "image/webp"} and info.get("thumburl"):
                candidates.append(info)
        rng.shuffle(candidates)
        for info in candidates[:2]:
            try:
                image = _download_photo(info["thumburl"])
                return PhotoOverlay(image, info.get("descriptionurl", "https://commons.wikimedia.org"),
                                    "Wikimedia Commons", search_term=term, search_offset=offset)
            except (requests.RequestException, OSError, ValueError):
                continue
        raise RuntimeError("搜索结果没有可下载的照片")
    except (requests.RequestException, OSError, ValueError, RuntimeError, TypeError) as error:
        backup = bundled_photo(rng, str(error))
        backup.search_term = term
        backup.search_offset = offset
        return backup
