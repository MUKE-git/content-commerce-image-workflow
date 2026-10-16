from io import BytesIO

from PIL import Image

from image_workflow.stickers import fetch_pexels_stickers


def test_pexels_search_downloads_images_once_per_batch(monkeypatch):
    buffer = BytesIO()
    Image.new("RGB", (16, 16), "red").save(buffer, "JPEG")
    calls = []

    class Response:
        def __init__(self, url):
            self.url = url

        def raise_for_status(self):
            pass

        def json(self):
            return {"photos": [{"src": {"small": "https://images.pexels.com/a.jpg"}}]}

        def iter_content(self, _size):
            yield buffer.getvalue()

        def close(self):
            pass

    def get(url, **kwargs):
        calls.append((url, kwargs))
        return Response(url)

    monkeypatch.setenv("PEXELS_API_KEY", "test-key")
    monkeypatch.setattr("image_workflow.stickers.requests.get", get)
    images = fetch_pexels_stickers("leaves", 4)
    assert len(images) == 1
    assert images[0].size == (16, 16)
    assert len(calls) == 2
    assert calls[0][1]["headers"]["Authorization"] == "test-key"
