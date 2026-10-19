import random
import threading
import time

from PIL import Image

from image_workflow.photo_calibration import online_wait_seconds
from image_workflow.stickers import PhotoCandidate, PhotoOverlay, PhotoPrefetchPool


def candidate(number):
    return PhotoCandidate(f"https://thumb.wikimedia.org/{number}.jpg",
                          f"https://commons.wikimedia.org/{number}", "texture", number)


def photo(item):
    return PhotoOverlay(Image.new("RGB", (16, 16), "blue"), item.source_url,
                        "Wikimedia Commons")


def test_first_completed_download_is_used_while_another_is_pending():
    release = threading.Event()
    second_started = threading.Event()

    def download(item):
        if item.search_offset == 2:
            second_started.set()
            assert release.wait(2)
        return photo(item)

    pool = PhotoPrefetchPool(2, 2, random.Random(1),
                             search=lambda _: [candidate(1), candidate(2)],
                             download=download)
    pool.start()
    try:
        assert second_started.wait(1)
        first = pool.next_photo(random.Random(1))
        assert first.source_url.endswith("/1")
        assert not release.is_set()
        release.set()
        second = pool.next_photo(random.Random(2))
        assert second.source_url.endswith("/2")
        assert first.source_url != second.source_url
    finally:
        release.set()
        pool.close()


def test_exhausted_search_uses_bundled_photo_without_waiting_for_deadline():
    pool = PhotoPrefetchPool(1, 10, random.Random(1), search=lambda _: [], download=photo)
    pool.start()
    try:
        started = time.monotonic()
        result = pool.next_photo(random.Random(1))
        assert time.monotonic() - started < 1
        assert result.source_name == "Pexels backup"
        assert pool.stats()["searches"] == 2
    finally:
        pool.close()


def test_deadline_falls_back_even_if_download_is_still_running():
    release = threading.Event()

    def download(item):
        release.wait(1)
        return photo(item)

    pool = PhotoPrefetchPool(1, 0.05, random.Random(1),
                             search=lambda _: [candidate(1)], download=download)
    pool.start()
    try:
        assert pool.next_photo(random.Random(1)).source_name == "Pexels backup"
    finally:
        release.set()
        pool.close()


def test_online_wait_interpolates_measured_sizes(monkeypatch):
    monkeypatch.setenv("PHOTO_FETCH_X_1", "10")
    monkeypatch.setenv("PHOTO_FETCH_X_5", "30")
    monkeypatch.setenv("PHOTO_FETCH_X_20", "90")
    assert online_wait_seconds(1) == 20
    assert online_wait_seconds(3) == 40
    assert online_wait_seconds(10) == 100
    assert online_wait_seconds(20) == 180


def test_download_attempts_stop_at_twice_batch_size():
    number = 0

    def search(_rng):
        nonlocal number
        found = [candidate(number + index) for index in range(5)]
        number += 5
        return found

    def download(_item):
        raise OSError("unavailable")

    pool = PhotoPrefetchPool(5, 3, random.Random(1), search=search, download=download)
    pool.start()
    try:
        assert pool.next_photo(random.Random(1)).source_name == "Pexels backup"
        stats = pool.stats()
        assert stats["download_attempts"] == 10
        assert stats["searches"] <= 2
    finally:
        pool.close()


def test_no_more_than_two_downloads_run_together():
    lock = threading.Lock()
    active = 0
    peak = 0

    def search(_rng):
        return [candidate(index) for index in range(5)]

    def download(item):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.02)
        with lock:
            active -= 1
        return photo(item)

    pool = PhotoPrefetchPool(5, 2, random.Random(1), search=search, download=download)
    pool.start()
    try:
        assert [pool.next_photo(random.Random(1)).source_name for _ in range(5)] == [
            "Wikimedia Commons"
        ] * 5
        assert 1 <= peak <= 2
    finally:
        pool.close()
