"""Write a PDF that contains only the pages counted in data/manifest.json,
plus a CSV mapping each new page to its original PDF page.

The pipeline and benchmark keep using ORIGINAL page numbers (gold_page = original
pdf_page). This subset file is only for reviewers who want to see the corpus pages.

Usage (from starter/):
    python scripts/extract_selected_pages.py
"""
import csv
import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "starter/data/intro-intellectual-property.pdf"
OUT_PDF = ROOT / "starter/data/selected-38-pages.pdf"
OUT_MAP = ROOT / "starter/data/selected-38-pages_page-map.csv"


def main() -> None:
    manifest = json.loads((ROOT / "data/manifest.json").read_text(encoding="utf-8"))[0]
    pages = manifest["pages"]
    reader = PdfReader(SRC)
    writer = PdfWriter()
    rows = []
    for new_page, p in enumerate(pages, start=1):
        writer.add_page(reader.pages[p["pdf_page"] - 1])  # pdf_page is 1-based
        rows.append({"new_page": new_page, "original_pdf_page": p["pdf_page"],
                     "page_id": p["page_id"], "chapter": p["chapter"],
                     "chapter_title": p.get("chapter_title", "")})
    writer.add_metadata({"/Title": "Introduction to Intellectual Property (OpenStax) - 38 selected pages",
                         "/Subject": "Unmodified pages from the OpenStax PDF, CC BY 4.0"})
    with OUT_PDF.open("wb") as f:
        writer.write(f)
    with OUT_MAP.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} pages -> {OUT_PDF.name} ({OUT_PDF.stat().st_size / 1e6:.1f} MB) and {OUT_MAP.name}")


if __name__ == "__main__":
    main()
