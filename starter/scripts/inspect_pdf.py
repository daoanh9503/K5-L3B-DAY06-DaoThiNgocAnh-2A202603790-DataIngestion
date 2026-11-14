"""Inspect a PDF before building the manifest: bookmarks (chapter/section -> page)
and per-page character counts. Page numbers printed are 1-based PDF page indices.

Usage (from starter/):
    python scripts/inspect_pdf.py data/intro-intellectual-property.pdf
Writes the same report to results/pdf_inspect.txt.
"""
import sys
import unicodedata
from pathlib import Path

from pypdf import PdfReader


def walk_outline(reader, items, depth=0, out=None):
    out = [] if out is None else out
    for item in items:
        if isinstance(item, list):
            walk_outline(reader, item, depth + 1, out)
        else:
            try:
                page = reader.get_destination_page_number(item) + 1
            except Exception:
                page = None
            out.append((depth, item.title, page))
    return out


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: python scripts/inspect_pdf.py <path-to-pdf>")
    path = Path(sys.argv[1])
    reader = PdfReader(path)
    lines = [f"File: {path} | physical pages: {len(reader.pages)}", "", "== OUTLINE (depth, PDF page, title) =="]

    outline = walk_outline(reader, reader.outline)
    if not outline:
        lines.append("(PDF has no bookmarks)")
    for depth, title, page in outline:
        lines.append(f"{'  ' * depth}p{page}\t{title}")

    lines += ["", "== PAGES (PDF page, chars, first words) =="]
    for i, p in enumerate(reader.pages, start=1):
        try:
            text = unicodedata.normalize("NFC", p.extract_text() or "")
        except Exception as e:  # record, don't hide, extraction errors
            lines.append(f"p{i}\tERROR\t{e}")
            continue
        preview = " ".join(text.split())[:70]
        flag = "  <-- EMPTY/SHORT" if len(text.strip()) < 300 else ""
        lines.append(f"p{i}\t{len(text)}\t{preview}{flag}")

    report = "\n".join(lines)
    out = Path("results/pdf_inspect.txt")
    out.parent.mkdir(exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
