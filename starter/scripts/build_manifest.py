"""Build data/manifest.json for the selected pages of the OpenStax PDF.

chapter/section values come from the PDF's own bookmarks (not guessed).
Run from starter/:  python scripts/build_manifest.py
"""
import json
import unicodedata
from pathlib import Path

from pypdf import PdfReader

PDF = Path("data/intro-intellectual-property.pdf")
OUT = Path("../data/manifest.json")

# Selected PDF pages (1-based physical page index), chosen from results/pdf_inspect.txt.
SELECTION = {
    "3": list(range(102, 104)) + list(range(114, 123)),   # 3.1, 3.4-3.7
    "4": [142] + list(range(147, 158)),                    # 4.1, 4.4-4.8
    "5": list(range(172, 187)),                            # 5.1-5.6
}
CHAPTER_TITLES = {"3": "Copyright Basics", "4": "Trademark Basics", "5": "Trade Secret Basics"}


def flat_outline(reader, items, out):
    for it in items:
        if isinstance(it, list):
            flat_outline(reader, it, out)
        else:
            out.append((it.title, reader.get_destination_page_number(it) + 1))
    return out


def main() -> None:
    reader = PdfReader(PDF)
    # numbered sections like "3.4 Eligible Works", sorted by start page
    sections = sorted(
        [(p, t) for t, p in flat_outline(reader, reader.outline, []) if t[:1].isdigit() and "." in t.split()[0]],
        key=lambda x: x[0],
    )

    pages, total = [], 0
    for chapter, nums in SELECTION.items():
        for n in nums:
            text = unicodedata.normalize("NFC", reader.pages[n - 1].extract_text() or "")
            starts_here = [t for p, t in sections if p == n and t.startswith(chapter + ".")]
            before = [t for p, t in sections if p < n and t.startswith(chapter + ".")]
            current = before[-1:] if before else []
            # page that opens with a new section heading carries no text of the previous one
            if starts_here and text.lstrip().startswith(starts_here[0].split()[0]):
                current = []
            pages.append({
                "page_id": f"iip-p{n}",
                "pdf_page": n,
                "chapter": chapter,
                "chapter_title": CHAPTER_TITLES[chapter],
                "sections": current + starts_here,  # section(s) whose text appears on this page
                "char_count": len(text),
            })
            total += len(text)

    manifest = [{
        "source_id": "openstax-iip",
        "title": "Introduction to Intellectual Property (OpenStax)",
        "source_path_or_url": "https://openstax.org/details/books/introduction-intellectual-property",
        "pdf_download_url": "https://assets.openstax.org/oscms-prodcms/media/documents/introduction-intellectual-property_-_WEB.pdf",
        "local_path": "starter/data/intro-intellectual-property.pdf (not committed; download from pdf_download_url)",
        "license_or_permission": "CC BY 4.0 — 'Textbook content is licensed under a Creative Commons Attribution 4.0 International License' (PDF page 4). Book notes it is derived from material by The Michelson 20MM Foundation, with changes.",
        "accessed_at": "2026-11-14",
        "physical_pages": len(reader.pages),
        "page_numbering": "pdf_page = 1-based physical page index in the PDF file (not the printed page number)",
        "page_rule": "Counted: body pages of the chosen sections of chapters 3, 4, 5 with >=1500 extracted chars or substantive prose. Excluded: cover, contents, preface, chapter-opener figure pages, Assessment Questions, Glossary, Answer Key, Index, and figure-dominated short pages (e.g. 107, 113, 143, 187).",
        "filter_field": {"name": "chapter", "type": "string", "values": list(SELECTION), "source": "PDF bookmarks (Chapter 3/4/5)"},
        "pages_counted": len(pages),
        "total_chars": total,
        "pages": pages,
    }]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"pages_counted={len(pages)} total_chars={total} -> {OUT}")
    short = [p for p in pages if p["char_count"] < 1500]
    print("pages under 1500 chars:", [(p["pdf_page"], p["char_count"]) for p in short])


if __name__ == "__main__":
    main()
