from io import BytesIO
from zipfile import ZipFile

import pytest
from PIL import Image

from image_workflow import ImageInput, process_batch, process_image
from image_workflow import ocr
from image_workflow.workflow import STAGES


def sample_image(color: str, fmt: str = "PNG") -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (120, 160), color).save(buffer, format=fmt)
    return buffer.getvalue()


def test_batch_keeps_results_isolated_and_exports_only_successes():
    stages = []
    items = [
        ImageInput("same.png", sample_image("red")),
        ImageInput("broken.png", b"not an image"),
        ImageInput("same.png", sample_image("blue")),
    ]
    batch = process_batch(
        items, text_detector=lambda _: True, sticker_fetcher=lambda _q, _n: [],
        seed=7, progress=lambda i, n, stage, name: stages.append((i, n, stage, name)),
    )
    assert len(batch.successful) == 2
    assert len(batch.failed) == 1
    assert batch.failed[0].input_name == "broken.png"
    assert batch.successful[0].output_name != batch.successful[1].output_name
    assert [event[2] for event in stages if event[0] == 1] == list(STAGES)
    assert all(image.details["flipped"] is False for image in batch.successful)
    with ZipFile(BytesIO(batch.to_zip())) as archive:
        assert archive.namelist() == [image.output_name for image in batch.successful]
        colors = []
        for name in archive.namelist():
            with Image.open(BytesIO(archive.read(name))) as image:
                assert image.size == (1280, 1706)
                colors.append(image.getpixel((640, 850)))
        assert colors[0][0] > colors[0][2]
        assert colors[1][2] > colors[1][0]


@pytest.mark.parametrize("detection", [True, None])
def test_text_or_uncertainty_keeps_original_orientation(detection):
    item = ImageInput("text.jpg", sample_image("white", "JPEG"))
    result = process_image(item, text_detector=lambda _: detection, seed=1)
    assert result.ok
    assert result.details["flipped"] is False


def test_batch_limit_and_sticker_failure_fallback():
    item = ImageInput("a.png", sample_image("green"))
    with pytest.raises(ValueError, match="20"):
        process_batch([item] * 21)
    batch = process_batch(
        [item], text_detector=lambda _: None,
        sticker_fetcher=lambda _q, _n: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    assert batch.successful[0].ok
    assert batch.sticker_source == "built-in"
    assert batch.sticker_error == "offline"


def test_twenty_images_and_online_sticker_branch():
    item = ImageInput("photo.webp", sample_image("yellow", "WEBP"))
    batch = process_batch(
        [item] * 20, text_detector=lambda _: False,
        sticker_fetcher=lambda _q, _n: [Image.new("RGB", (40, 40), "purple")],
        seed=12,
    )
    assert len(batch.successful) == 20
    assert batch.sticker_source == "Pexels"
    assert len({image.output_name for image in batch.successful}) == 20


def test_ocr_only_marks_clear_text_free_images_as_safe_to_flip(monkeypatch):
    class Detection:
        boxes = [1]
        txts = ("商品名称",)
        scores = (0.9,)

    monkeypatch.setattr(ocr, "_rapidocr", lambda: lambda _: Detection())
    image = Image.new("RGB", (100, 100), "white")
    assert ocr.detect_text(image) is True
    Detection.scores = (0.1,)
    assert ocr.detect_text(image) is None
    Detection.boxes = []
    assert ocr.detect_text(image) is False
