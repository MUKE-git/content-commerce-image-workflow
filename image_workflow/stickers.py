"""Randomly prefetch real overlay photos for a batch of images."""

from __future__ import annotations

import math
import random
import queue
import threading
import time
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


@dataclass(frozen=True)
class PhotoCandidate:
    thumbnail_url: str
    source_url: str
    search_term: str
    search_offset: int


def search_photos(rng: random.Random) -> list[PhotoCandidate]:
    """Return up to five randomly ordered Commons candidates from one search."""
    term = rng.choice(SEARCH_TERMS)
    offset = rng.randrange(32)
    response = requests.get(
        COMMONS_API,
        params={
            "action": "query", "generator": "search", "gsrsearch": f"filetype:bitmap {term}",
            "gsrnamespace": 6, "gsroffset": offset, "gsrlimit": 8,
            "prop": "imageinfo", "iiprop": "url|mime", "iiurlwidth": 1280,
            "format": "json", "formatversion": 2,
        },
        headers=HEADERS, timeout=(5, 10),
    )
    try:
        response.raise_for_status()
        pages = response.json().get("query", {}).get("pages", [])
    finally:
        response.close()
    candidates = []
    for page in pages:
        if not page.get("imageinfo"):
            continue
        info = page["imageinfo"][0]
        if info.get("mime") in {"image/jpeg", "image/png", "image/webp"} and info.get("thumburl"):
            candidates.append(PhotoCandidate(
                info["thumburl"], info.get("descriptionurl", "https://commons.wikimedia.org"),
                term, offset,
            ))
    rng.shuffle(candidates)
    return candidates[:5]


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
    response = requests.get(url, headers=HEADERS, timeout=(5, 10), stream=True)
    started = time.monotonic()
    try:
        response.raise_for_status()
        content = bytearray()
        for chunk in response.iter_content(64 * 1024):
            if time.monotonic() - started > 20:
                raise TimeoutError("照片下载超过 20 秒")
            content.extend(chunk)
            if len(content) > MAX_DOWNLOAD_BYTES:
                raise ValueError("照片超过下载上限")
        with Image.open(BytesIO(content)) as image:
            if image.width * image.height > 30_000_000:
                raise ValueError("照片像素过大")
            return image.convert("RGB")
    finally:
        response.close()


def download_photo(candidate: PhotoCandidate) -> PhotoOverlay:
    return PhotoOverlay(
        _download_photo(candidate.thumbnail_url), candidate.source_url, "Wikimedia Commons",
        search_term=candidate.search_term, search_offset=candidate.search_offset,
    )


class PhotoPrefetchPool:
    """Batch-local search and download pipeline; ready photos are handed out once."""

    def __init__(self, count: int, seconds: float, rng: random.Random,
                 search=search_photos, download=download_photo,
                 attempt_limit: int | None = None):
        self.count = count
        self.deadline = time.monotonic() + seconds
        self.rng = rng
        self.search = search
        self.download = download
        self.attempt_limit = attempt_limit if attempt_limit is not None else 2 * count
        self.candidates: queue.Queue[PhotoCandidate] = queue.Queue(maxsize=8)
        self.ready: queue.Queue[PhotoOverlay] = queue.Queue(maxsize=count)
        self.stop = threading.Event()
        self.search_done = threading.Event()
        self.download_done = threading.Event()
        self.lock = threading.Lock()
        self.searches = 0
        self.attempts = 0
        self.online = 0
        self.first_photo_seconds: float | None = None
        self.errors: list[str] = []
        self._finished_workers = 0
        self.started = time.monotonic()
        self.threads: list[threading.Thread] = []

    def start(self) -> None:
        self.threads = [
            threading.Thread(target=self._search_loop, daemon=True),
            threading.Thread(target=self._download_loop, daemon=True),
            threading.Thread(target=self._download_loop, daemon=True),
        ]
        for thread in self.threads:
            thread.start()

    def _active(self) -> bool:
        return not self.stop.is_set() and time.monotonic() < self.deadline

    def _search_loop(self) -> None:
        scheduled = 0
        seen_urls: set[str] = set()
        try:
            for _ in range(2 * math.ceil(self.count / 5)):
                if not self._active() or scheduled >= self.attempt_limit:
                    break
                with self.lock:
                    self.searches += 1
                try:
                    candidates = self.search(self.rng)
                except Exception as error:
                    with self.lock:
                        self.errors.append(f"搜索失败: {error}")
                    continue
                for candidate in candidates:
                    if not self._active() or scheduled >= self.attempt_limit:
                        break
                    if candidate.thumbnail_url in seen_urls:
                        continue
                    while self._active():
                        try:
                            self.candidates.put(candidate, timeout=0.1)
                            seen_urls.add(candidate.thumbnail_url)
                            scheduled += 1
                            break
                        except queue.Full:
                            pass
        finally:
            self.search_done.set()

    def _download_loop(self) -> None:
        try:
            while self._active():
                with self.lock:
                    if self.online >= self.count or self.attempts >= self.attempt_limit:
                        return
                try:
                    candidate = self.candidates.get(timeout=0.1)
                except queue.Empty:
                    if self.search_done.is_set():
                        return
                    continue
                with self.lock:
                    if self.attempts >= self.attempt_limit or self.online >= self.count:
                        return
                    self.attempts += 1
                try:
                    photo = self.download(candidate)
                    if not self._active():
                        return
                    with self.lock:
                        if self.online < self.count:
                            self.online += 1
                            if self.first_photo_seconds is None:
                                self.first_photo_seconds = time.monotonic() - self.started
                            self.ready.put_nowait(photo)
                            if self.online >= self.count:
                                self.stop.set()
                except Exception as error:
                    with self.lock:
                        self.errors.append(f"下载失败: {error}")
        finally:
            with self.lock:
                self._finished_workers += 1
                if self._finished_workers == 2:
                    self.download_done.set()

    def next_photo(self, rng: random.Random) -> PhotoOverlay:
        while True:
            try:
                return self.ready.get_nowait()
            except queue.Empty:
                pass
            if time.monotonic() >= self.deadline or self.download_done.is_set():
                with self.lock:
                    reason = self.errors[-1] if self.errors else "在线照片未在等待窗口内取得"
                return bundled_photo(rng, reason)
            try:
                return self.ready.get(timeout=max(0.001, min(0.1, self.deadline - time.monotonic())))
            except queue.Empty:
                pass

    def close(self) -> None:
        self.stop.set()
        # Requests cannot be cancelled mid-read; daemon workers exit after their current call.
        # Do not extend the user's wait window for a slow network socket.
        deadline = time.monotonic() + 0.5
        for thread in self.threads:
            thread.join(timeout=max(0, deadline - time.monotonic()))

    def stats(self) -> dict[str, object]:
        with self.lock:
            return {
                "searches": self.searches, "download_attempts": self.attempts,
                "online_downloads": self.online,
                "first_photo_seconds": self.first_photo_seconds,
                "errors": list(self.errors),
            }


def random_photo(rng: random.Random) -> PhotoOverlay:
    """Compatibility helper for callers processing a single photo directly."""
    try:
        candidates = search_photos(rng)
        for candidate in candidates[:2]:
            try:
                return download_photo(candidate)
            except (requests.RequestException, OSError, ValueError):
                continue
        raise RuntimeError("搜索结果没有可下载的照片")
    except (requests.RequestException, OSError, ValueError, RuntimeError, TypeError) as error:
        return bundled_photo(rng, str(error))
