"""
Reading PDFs whose text can't be trusted: scans, and old fonts that extract as garbage.

Each page is checked. Good pages keep their text. The rest are read twice by Tesseract in two
different ways, and a figure the two reads don't agree on becomes "[unclear figure]", so a misread
can't reach an answer as fact. Results are saved beside the documents, because reading is slow.
"""

from __future__ import annotations

import io
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from .languages import western_digits

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "documents" / ".scans"
TESSDATA = ROOT / "data" / "tessdata"
TESSERACT = os.environ.get("TESSERACT_CMD") or r"C:\Program Files\Tesseract-OCR\tesseract.exe"
UNCLEAR = "[unclear figure]"
LANGUAGES = {"AP": "tel", "TS": "tel", "TN": "tam", "PY": "tam", "KA": "kan", "MH": "mar", "GA": "mar"}
MOST = "hin"  # official orders elsewhere are mostly English or Hindi; add more as they're needed

_NUMBER = re.compile(r"\d[\d,./-]*\d")
# Accented Latin and private-use letters are what old Indian fonts turn into when extracted.
_GARBLED = re.compile(r"[\u0080-\u02ff\ue000-\uf8ff\ufffd]|\(cid:\d+\)")
_MOST_GARBLED = 0.03
_LITTLE_TEXT = 40


@dataclass
class Reading:
    text: str
    pages: int
    read_as_scan: int
    unclear: int


def page_problem(text: str) -> str:
    """Why a page's text can't be trusted, or nothing."""
    letters = re.sub(r"\s", "", text)
    if len(letters) < _LITTLE_TEXT:
        return "no text"
    if len(_GARBLED.findall(letters)) / len(letters) > _MOST_GARBLED:
        return "garbled"
    return ""


def languages_for(state: str) -> str:
    wanted = ["eng", LANGUAGES.get(state, MOST)]
    return "+".join(w for w in wanted if (TESSDATA / f"{w}.traineddata").exists()) or "eng"


def _numbers(text: str) -> set[str]:
    return {re.sub(r"[,./-]", "", n) for n in _NUMBER.findall(text)}


def agree(first: str, second: str) -> tuple[str, int]:
    """The first read, with figures of two or more digits the second read doesn't have marked unclear."""
    first, second = western_digits(first), western_digits(second)  # the figure checks read 0-9
    others, unclear = _numbers(second), 0

    def mark(m: re.Match) -> str:
        nonlocal unclear
        if re.sub(r"[,./-]", "", m.group(0)) in others:
            return m.group(0)
        unclear += 1
        return UNCLEAR
    return _NUMBER.sub(mark, first), unclear


def _read_page(page, languages: str) -> tuple[str, int]:
    import pytesseract
    from PIL import Image

    pytesseract.pytesseract.tesseract_cmd = TESSERACT
    os.environ["TESSDATA_PREFIX"] = str(TESSDATA)
    def read(dpi: int, mode: int) -> str:
        image = Image.open(io.BytesIO(page.get_pixmap(dpi=dpi).tobytes("png")))
        return pytesseract.image_to_string(image, lang=languages, config=f"--psm {mode}")
    return agree(read(300, 3), read(200, 6))


def has_picture(page) -> bool:
    return bool(page.get_images())


def read(path: Path, state: str, digest: str, force: bool = False) -> Reading | None:
    """
    A PDF's text with bad pages read as scans. None if every page is fine, so nothing changes.
    force reads every page: some fonts swap letters while still looking like real text, which
    only reading can show. Maharashtra's order extracted "vima" in Marathi as "rima".
    """
    import fitz
    from pypdf import PdfReader

    layer = [p.extract_text() or "" for p in PdfReader(path).pages]
    document = fitz.open(path)
    bad = list(range(len(layer))) if force else [
        n for n, text in enumerate(layer)
        if page_problem(text) == "garbled" or (page_problem(text) and has_picture(document[n]))]
    if not bad:
        return None
    if not Path(TESSERACT).exists():
        raise FileNotFoundError(f"{path.name} needs scan reading, but Tesseract isn't at {TESSERACT}")
    saved = CACHE / f"{digest}.json"
    done = json.loads(saved.read_text(encoding="utf-8")) if saved.exists() else {}
    languages = languages_for(state)
    unclear = 0
    for n in bad:
        if str(n) not in done:
            done[str(n)] = _read_page(document[n], languages)
            CACHE.mkdir(parents=True, exist_ok=True)
            saved.write_text(json.dumps(done, ensure_ascii=False), encoding="utf-8")
        layer[n] = done[str(n)][0]
        unclear += done[str(n)][1]
    return Reading("\n".join(layer), len(layer), len(bad), unclear)
