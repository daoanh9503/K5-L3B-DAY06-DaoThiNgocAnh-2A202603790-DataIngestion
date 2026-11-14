"""Automatic evidence-hit scoring and per-query traces.

A retrieved chunk is a hit when it comes from the gold source + page AND contains the whole
gold evidence quote (whitespace/case-normalized). Coherence and grounding are NOT inferred here;
they are labeled manually.
"""
import unicodedata
from typing import Any


def _norm(s: str) -> str:
    return " ".join(unicodedata.normalize("NFC", s).split()).lower()


def _golds(q: dict[str, Any]) -> list[tuple[str, int, str]]:
    golds = [(q["gold_source_id"], int(q["gold_page"]), q["evidence_quote"])]
    for alt in q.get("alternative_gold", []):  # optional documented alternatives
        golds.append((alt["gold_source_id"], int(alt["gold_page"]), alt["evidence_quote"]))
    return golds


def is_hit(q: dict[str, Any], hit: dict[str, Any]) -> bool:
    meta = hit["metadata"]
    return any(meta["document_id"] == src and int(meta["page"]) == page and _norm(ev) in _norm(hit["text"])
               for src, page, ev in _golds(q))


def page_match(q: dict[str, Any], hit: dict[str, Any]) -> bool:
    meta = hit["metadata"]
    return any(meta["document_id"] == src and int(meta["page"]) == page for src, page, _ in _golds(q))


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    flags = [is_hit(question, h) for h in hits]
    pages = [page_match(question, h) for h in hits]
    filt = question.get("filter")
    return {
        "hit_at_1": bool(flags[:1] and flags[0]),
        "hit_at_3": any(flags[:3]),
        "page_hit_at_3": any(pages[:3]),
        # gold page retrieved but evidence not fully inside one chunk -> likely split across chunks
        "evidence_split_suspect": any(pages[:3]) and not any(flags[:3]),
        "per_rank_hit": flags,
        "filter_compliant": None if not filt else all(
            all(str(h["metadata"].get(k)) == str(v) for k, v in filt.items()) for h in hits),
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for t in traces:
        key = f"{t['strategy']}/{t['split']}"
        s = out.setdefault(key, {"n": 0, "hit_at_1": 0, "hit_at_3": 0, "page_hit_at_3": 0,
                                 "evidence_split_suspect": 0, "filter_q": 0, "filter_compliant": 0})
        s["n"] += 1
        for k in ("hit_at_1", "hit_at_3", "page_hit_at_3", "evidence_split_suspect"):
            s[k] += int(t["eval"][k])
        if t["eval"]["filter_compliant"] is not None:
            s["filter_q"] += 1
            s["filter_compliant"] += int(t["eval"]["filter_compliant"])
    for s in out.values():
        s["Hit@1"] = f"{s['hit_at_1']}/{s['n']}"
        s["Hit@3"] = f"{s['hit_at_3']}/{s['n']}"
        s["filter"] = f"{s['filter_compliant']}/{s['filter_q']}" if s["filter_q"] else "N/A"
    return out
