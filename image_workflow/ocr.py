"""Conservative text detection: an uncertain result never permits mirroring."""

from __future__ import annotations

import shutil
import subprocess
from functools import lru_cache
from io import BytesIO

from PIL import Image

TEXT_SCORE_THRESHOLD = 0.35  # Provisional; validate against labeled product images.


@lru_cache(maxsize=1)
def _rapidocr():
    from rapidocr import RapidOCR

    return RapidOCR()


def detect_text(image: Image.Image) -> bool | None:
    """Detect Chinese/English text, preserving orientation when uncertain."""
    try:
        result = _rapidocr()(image)
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return False
        scores = result.scores or ()
        texts = result.txts or ()
        if any(text.strip() and score >= TEXT_SCORE_THRESHOLD for text, score in zip(texts, scores)):
            return True
        return None
    except (ImportError, OSError, RuntimeError):
        return _tesseract_detect_text(image)


def _tesseract_detect_text(image: Image.Image) -> bool | None:
    """Use Tesseract if installed; missing OCR yields an uncertain result."""
    executable = shutil.which("tesseract")
    if executable is None:
        return None
    try:
        languages = subprocess.run(
            [executable, "--list-langs"], capture_output=True, text=True,
            timeout=10, check=True,
        ).stdout
        if not {"chi_sim", "eng"}.issubset(set(languages.splitlines())):
            return None
        buffer = BytesIO()
        image.convert("RGB").save(buffer, format="PNG")
        result = subprocess.run(
            [executable, "stdin", "stdout", "-l", "chi_sim+eng", "tsv"],
            input=buffer.getvalue(), capture_output=True, timeout=30, check=True,
        )
        rows = result.stdout.decode("utf-8", errors="replace").splitlines()
        for row in rows[1:]:
            cells = row.split("\t", 11)
            if len(cells) == 12 and cells[11].strip():
                try:
                    if float(cells[10]) >= 35:
                        return True
                except ValueError:
                    continue
        return False
    except (OSError, subprocess.SubprocessError):
        return None
