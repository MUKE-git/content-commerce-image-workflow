import random
from io import BytesIO

from PIL import Image

from image_workflow import stickers


def test_four_approved_photos_are_downloaded_and_readable():
    assert len(stickers.PEXELS_PAGES) == 4
    for name in stickers.PEXELS_PAGES:
        with Image.open(stickers.PHOTO_DIR / f"{name}.jpg") as photo:
            photo.verify()


def test_random_search_uses_a_fresh_query_per_image(monkeypatch):
    buffer = BytesIO()
    Image.new("RGB", (32, 32), "red").save(buffer, "JPEG")
    searches = []

    class Response:
        def __init__(self, is_search):
            self.is_search = is_search

        def raise_for_status(self):
            pass

        def json(self):
            return {"query": {"pages": [{"imageinfo": [{
                "mime": "image/jpeg",
                "thumburl": "https://thumb.wikimedia.org/example.jpg",
                "descriptionurl": "https://commons.wikimedia.org/wiki/File:Example.jpg",
            }]}]}}

        def iter_content(self, _size):
            yield buffer.getvalue()

        def close(self):
            pass

    def get(url, **kwargs):
        if url == stickers.COMMONS_API:
            searches.append(kwargs["params"])
            return Response(True)
        assert url == "https://thumb.wikimedia.org/example.jpg"
        return Response(False)

    monkeypatch.setattr(stickers.requests, "get", get)
    for seed in (1, 2):
        result = stickers.random_photo(random.Random(seed))
        assert result.source_name == "Wikimedia Commons"
        assert result.image.size == (32, 32)
    assert len(searches) == 2
    assert searches[0]["gsrsearch"] != searches[1]["gsrsearch"] or searches[0]["gsroffset"] != searches[1]["gsroffset"]
