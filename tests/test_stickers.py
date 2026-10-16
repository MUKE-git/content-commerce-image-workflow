from io import BytesIO

from PIL import Image

from image_workflow.stickers import fetch_openverse_stickers


def test_openverse_search_downloads_public_domain_images_once_per_batch(monkeypatch):
    buffer = BytesIO()
    Image.new("RGB", (16, 16), "red").save(buffer, "JPEG")
    calls = []

    class Response:
        def __init__(self, url):
            self.url = url

        def raise_for_status(self):
            pass

        def json(self):
            return {"results": [
                {"id": "4bc43a04-ef46-4544-a0c1-63c63f56e276", "license": "cc0", "mature": False},
                {"id": "610756ec-ae31-4d5e-8f03-8cc52f31b71d", "license": "by-nc", "mature": False},
            ]}

        def iter_content(self, _size):
            yield buffer.getvalue()

        def close(self):
            pass

    def get(url, **kwargs):
        calls.append((url, kwargs))
        return Response(url)

    monkeypatch.setattr("image_workflow.stickers.requests.get", get)
    images = fetch_openverse_stickers("leaves", 4)
    assert len(images) == 1
    assert images[0].size == (16, 16)
    assert len(calls) == 2
    assert calls[0][1]["params"]["license"] == "cc0,pdm"
    assert calls[1][0] == "https://api.openverse.org/v1/images/4bc43a04-ef46-4544-a0c1-63c63f56e276/thumb/"
