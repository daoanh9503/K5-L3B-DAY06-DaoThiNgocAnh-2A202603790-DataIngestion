"""Strategy A: fixed-size character windows. Strategy B: structure-aware (heading + sentence) chunks.

pypdf does not emit blank lines between paragraphs, so B uses headings (short lines with no
final punctuation, e.g. "First-Sale Doctrine") as block boundaries and never cuts a sentence
unless the sentence alone exceeds max_size.
"""
import re

from .models import Chunk, DocumentPage

_SENT_SPLIT = re.compile(r"(?<=[.!?”\"])\s+(?=[A-Z“\"(])")


def _chunk(page: DocumentPage, tag: str, i: int, text: str) -> Chunk:
    return Chunk(
        chunk_id=f"{page.document_id}-p{page.page}-{tag}{i:02d}",  # stable across re-runs
        document_id=page.document_id, source=page.source, page=page.page,
        text=text, metadata={**page.metadata, "char_len": len(text)},
    )


def fixed_size(page: DocumentPage, size: int = 500, overlap: int = 50) -> list[Chunk]:
    if not 0 <= overlap < size:
        raise ValueError("need 0 <= overlap < size")
    text = " ".join(page.text.split())
    out, start = [], 0
    while start < len(text):
        out.append(_chunk(page, "f", len(out), text[start:start + size]))
        if start + size >= len(text):
            break
        start += size - overlap
    return out


def _is_heading(line: str) -> bool:
    return (len(line) <= 70 and line[:1].isupper() and not line.rstrip().endswith((".", ",", ";", ":", "?", "!"))
            and len(line.split()) <= 9)


def _blocks(text: str) -> list[str]:
    """Group lines into blocks that start at headings."""
    blocks, cur = [], []
    for line in text.splitlines():
        if _is_heading(line) and cur:
            blocks.append(" ".join(cur))
            cur = []
        cur.append(line.strip())
    if cur:
        blocks.append(" ".join(cur))
    return [b for b in blocks if b.strip()]


def by_paragraph(page: DocumentPage, max_size: int = 800) -> list[Chunk]:
    out = []
    for block in _blocks(page.text):
        buf = ""
        for sent in _SENT_SPLIT.split(block):
            if len(sent) > max_size:  # oversized sentence: flush, then hard-split it
                if buf:
                    out.append(buf)
                    buf = ""
                out.extend(sent[i:i + max_size] for i in range(0, len(sent), max_size))
            elif len(buf) + len(sent) + 1 <= max_size:
                buf = f"{buf} {sent}".strip()
            else:
                out.append(buf)
                buf = sent
        if buf:
            out.append(buf)
    # merge tiny leftovers (e.g. a lone heading) into the next chunk when it fits
    merged: list[str] = []
    for t in out:
        if merged and len(merged[-1]) < 120 and len(merged[-1]) + len(t) + 1 <= max_size:
            merged[-1] = f"{merged[-1]} {t}"
        else:
            merged.append(t)
    return [_chunk(page, "p", i, t) for i, t in enumerate(merged)]
