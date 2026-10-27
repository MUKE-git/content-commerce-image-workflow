from pathlib import Path

import pytest
from PIL import Image

from similarity_test.compare import compare


def test_identical_images_score_100(tmp_path: Path):
    path = tmp_path / "sample.png"
    Image.new("RGB", (40, 60), (15, 100, 230)).save(path)
    result = compare(path, path)
    assert result["metrics"]["MSE"] == 0
    assert result["metrics"]["PSNR_dB"] is None
    assert result["similarity_score"] == 100
    assert result["verdict"] == "重复"


def test_unreadable_image_does_not_receive_a_verdict(tmp_path: Path):
    good = tmp_path / "good.png"
    bad = tmp_path / "bad.png"
    Image.new("RGB", (40, 60), "white").save(good)
    bad.write_bytes(b"not an image")
    with pytest.raises(ValueError, match="无法读取图片"):
        compare(good, bad)
