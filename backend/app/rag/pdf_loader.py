"""PDF text extraction.

Deliberately small: `pypdf` reads the text layer, and that is all. A scanned,
image-only resume has no text layer, so extraction returns an empty string and
the caller raises a clear "no readable text" error instead of feeding an empty
document to the LLM. OCR would be the Phase 2 answer.
"""
import logging
import re
from pathlib import Path
from typing import Tuple

from pypdf import PdfReader

from app.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

# Resumes routinely use these as bullet glyphs; they add nothing for the model.
_BULLETS = re.compile(r"[•●▪◦⁃]")
_WHITESPACE = re.compile(r"[ \t]+")
_BLANK_LINES = re.compile(r"\n{3,}")


def extract_pdf_text(path: Path) -> Tuple[str, int]:
    """Return `(clean_text, page_count)`."""
    try:
        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:  # pypdf raises a wide range of parse errors
        logger.warning("PDF parse failed for %s: %s", path.name, exc)
        raise ValidationError("Could not read that PDF. Please upload a text-based PDF.") from exc

    text = clean_text("\n".join(pages))
    if len(text) < 50:
        raise ValidationError(
            "No readable text found in this PDF. It looks like a scanned image; "
            "please upload a text-based PDF."
        )
    return text, len(pages)


def clean_text(raw: str) -> str:
    text = _BULLETS.sub("-", raw)
    text = _WHITESPACE.sub(" ", text)
    text = _BLANK_LINES.sub("\n\n", text)
    return text.strip()
