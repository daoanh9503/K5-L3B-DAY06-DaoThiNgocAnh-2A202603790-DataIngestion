"""Read and normalize the PDF pages listed in data/manifest.json."""
import logging
import re
import unicodedata
from pathlib import Path

from pypdf import PdfReader

from .models import DocumentPage

log = logging.getLogger(__name__)

# Running header/footer lines printed by OpenStax on every page.
_FOOTER_PATTERNS = [
    re.compile(r"^Access for free at openstax\.org\s*$"),
    re.compile(r"^\d+(\.\d+)?\s*•\s.*\s\d+\s*$"),   # "3.5 • Rights and Term     109"
    re.compile(r"^\d+\s+\d+\s*•\s.*$"),               # "108     3 • Copyright Basics"
]
# Endnote block at the bottom of a page starts with a roman numeral + 2 spaces: "xviii  John Wiley ..."
_ENDNOTE_START = re.compile(r"^[ivxlc]+\s{2,}\S")


def normalize_text(text: str) -> str:
    """NFC-normalize, drop running headers/footers and the endnote block, keep line breaks."""
    text = unicodedata.normalize("NFC", text).replace("­", "")
    kept = []
    for raw_line in text.splitlines():
        if _ENDNOTE_START.match(raw_line.strip()):
            break  # everything after the first endnote line is endnotes
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if not line or any(p.match(line) for p in _FOOTER_PATTERNS):
            continue
        kept.append(line)
    text = "\n".join(kept)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)  # re-join words hyphenated across lines
    return text.strip()


def load_pdf(path: Path, document_id: str, source: str, page_meta: list[dict]) -> list[DocumentPage]:
    """Extract the manifest-listed pages, keeping PDF page number, chapter and sections.

    Empty/failed pages are logged and skipped, never silently replaced.
    """
    if not path.exists():
        raise FileNotFoundError(f"{path} missing - download it from the manifest's pdf_download_url")
    reader = PdfReader(path)
    pages = []
    for meta in page_meta:
        n = meta["pdf_page"]
        try:
            raw = reader.pages[n - 1].extract_text() or ""
        except Exception as e:  # noqa: BLE001 - record any extraction failure
            log.error("extract failed: %s page %d: %s", source, n, e)
            continue
        text = normalize_text(raw)
        if len(text) < 300:
            log.warning("empty/short page skipped: %s page %d (%d chars)", source, n, len(text))
            continue
        pages.append(DocumentPage(
            document_id=document_id, source=source, page=n, text=text,
            metadata={"chapter": meta["chapter"], "section": " | ".join(meta["sections"]),
                      "page_id": meta["page_id"]},
        ))
    log.info("loaded %d/%d pages from %s", len(pages), len(page_meta), source)
    return pages
