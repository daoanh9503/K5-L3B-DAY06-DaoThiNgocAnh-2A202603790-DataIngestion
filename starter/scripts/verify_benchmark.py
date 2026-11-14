"""Check every evidence_quote exists on its gold_page (after whitespace normalization),
and that split/filter requirements hold. Run from starter/: python scripts/verify_benchmark.py
"""
import json
import unicodedata
from pathlib import Path

from pypdf import PdfReader

PDF = Path("data/intro-intellectual-property.pdf")
QUESTIONS = Path("../benchmark/questions.json")
MANIFEST = Path("../data/manifest.json")


def norm(s: str) -> str:
    return " ".join(unicodedata.normalize("NFC", s).split()).lower()


def main() -> None:
    reader = PdfReader(PDF)
    qs = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    pages = {p["pdf_page"]: p for p in json.loads(MANIFEST.read_text(encoding="utf-8"))[0]["pages"]}
    ok = True
    for q in qs:
        page = q["gold_page"]
        problems = []
        if page not in pages:
            problems.append("gold_page not in manifest")
        text = norm(reader.pages[page - 1].extract_text() or "")
        if norm(q["evidence_quote"]) not in text:
            problems.append("evidence NOT found on page")
        f = q.get("filter")
        if f and page in pages and pages[page]["chapter"] != f["chapter"]:
            problems.append("filter chapter does not match gold page")
        ok &= not problems
        print(f"{q['id']} {q['split']:4} p{page}: {'OK' if not problems else '; '.join(problems)}")
    dev = sum(q["split"] == "dev" for q in qs)
    test = sum(q["split"] == "test" for q in qs)
    filt = [q for q in qs if q.get("filter")]
    print(f"\ntotal={len(qs)} dev={dev} test={test} filter={len(filt)} "
          f"(test with filter={sum(q['split'] == 'test' for q in filt)})")
    print("ALL OK" if ok else "SOME CHECKS FAILED")


if __name__ == "__main__":
    main()
