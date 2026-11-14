"""Day 06 pipeline: ingest -> chunk (A, B) -> embed -> Chroma -> retrieve A/B/C -> traces + metrics.

Run from starter/:  python -m src.run
  A: fixed 500 chars, overlap 50, no filter        (index "A")
  B: structure-aware <= 800 chars, no filter       (index "B")
  C: same index as B + chapter filter, applied only to questions that carry a filter
"""
import csv
import json
import logging
import platform
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from statistics import mean, median

from .chunking import by_paragraph, fixed_size
from .embeddings import E5Embedder
from .evaluation import evaluate_query, summarize
from .ingestion import load_pdf

ROOT = Path(__file__).resolve().parents[2]
STARTER = ROOT / "starter"
RESULTS = STARTER / "results"
MODEL = "intfloat/multilingual-e5-small"
STRATEGIES = {
    "A": {"index": "A", "chunking": "fixed_size", "size": 500, "overlap": 50, "use_filter": False},
    "B": {"index": "B", "chunking": "by_paragraph", "size": 800, "overlap": 0, "use_filter": False},
    "C": {"index": "B", "chunking": "by_paragraph", "size": 800, "overlap": 0, "use_filter": True},
}


def build_chunks(pages, cfg):
    if cfg["chunking"] == "fixed_size":
        return [c for p in pages for c in fixed_size(p, cfg["size"], cfg["overlap"])]
    return [c for p in pages for c in by_paragraph(p, cfg["size"])]


def length_stats(chunks):
    lens = sorted(len(c.text) for c in chunks)
    return {"chunks": len(lens), "total_chars": sum(lens), "min": lens[0], "median": median(lens),
            "mean": round(mean(lens), 1), "max": lens[-1],
            "approx_tokens": round(sum(lens) / 4)}  # rough 4 chars/token estimate


def coherence_samples(pages, chunks_by_index):
    """Same 10 source positions for every strategy: middle of the first 10 counted pages (by pdf_page)."""
    rows = []
    for p in sorted(pages, key=lambda x: x.page)[:10]:
        words = p.text.split()
        mid = len(words) // 2
        probe = " ".join(words[mid:mid + 6]).lower()
        for strat, cfg in STRATEGIES.items():
            if strat == "C":
                continue  # C uses B's chunks, same coherence
            cands = [c for c in chunks_by_index[cfg["index"]]
                     if c.page == p.page and probe in " ".join(c.text.split()).lower()]
            note = ""
            if not cands:  # position straddles a chunk boundary: take the chunk holding its first words
                short = " ".join(words[mid:mid + 2]).lower()
                cands = [c for c in chunks_by_index[cfg["index"]]
                         if c.page == p.page and short in " ".join(c.text.split()).lower()]
                note = "probe split across chunks; chunk holding first words shown"
            c = cands[0] if cands else None
            rows.append({"position": f"p{p.page}@word{mid}", "probe": probe, "strategy": strat, "note": note,
                         "chunk_id": c.chunk_id if c else "NOT_FOUND",
                         "chunk_text": c.text if c else "", "score_0_2": "", "reason": ""})
    return rows


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler(RESULTS / "ingest_log.txt", mode="w", encoding="utf-8"),
                                  logging.StreamHandler()])
    log = logging.getLogger("run")

    manifest = json.loads((ROOT / "data/manifest.json").read_text(encoding="utf-8"))[0]
    questions = json.loads((ROOT / "benchmark/questions.json").read_text(encoding="utf-8"))
    if len(questions) < 20:
        raise SystemExit("benchmark needs >= 20 questions")

    pdf = STARTER / "data/intro-intellectual-property.pdf"
    t0 = time.perf_counter()
    pages = load_pdf(pdf, manifest["source_id"], pdf.name, manifest["pages"])
    if len(pages) < 30:
        raise SystemExit(f"only {len(pages)} content pages loaded; need >= 30")
    load_s = time.perf_counter() - t0

    from .store import ChromaStore  # import after logging is configured
    embedder = E5Embedder(MODEL)
    store = ChromaStore(str(STARTER / "chroma_db"), embedder.dimensions)

    chunks_by_index, stats = {}, {}
    for strat, cfg in STRATEGIES.items():
        idx = cfg["index"]
        if idx in chunks_by_index:
            stats[strat] = {**stats[idx], "note": f"reuses index {idx}; ingest cost counted once"}
            continue
        chunks = build_chunks(pages, cfg)
        t = time.perf_counter()
        vectors = embedder.embed_documents([c.text for c in chunks])
        embed_s = time.perf_counter() - t
        store.upsert(idx, chunks, vectors)
        first = store.count(idx)
        store.upsert(idx, chunks, vectors)  # re-ingest same version: count must not change
        second = store.count(idx)
        if first != second or first != len(chunks):
            raise SystemExit(f"duplicate check failed for {idx}: {len(chunks)} chunks, {first} -> {second}")
        chunks_by_index[idx] = chunks
        stats[strat] = {**length_stats(chunks), "embed_seconds": round(embed_s, 1),
                        "reingest_count_before_after": [first, second], "cost_usd": 0}
        log.info("index %s: %d chunks, embed %.1fs, re-ingest count %d -> %d", idx, len(chunks), embed_s, first, second)

    traces = []
    for strat, cfg in STRATEGIES.items():
        with open(RESULTS / f"traces_{strat}.jsonl", "w", encoding="utf-8") as f:
            for q in questions:
                filt = q.get("filter") if cfg["use_filter"] else None
                hits = store.search(cfg["index"], embedder.embed_query(q["question"]), 3, filt)
                rec = {"strategy": strat, "id": q["id"], "split": q["split"], "type": q.get("type"),
                       "question": q["question"], "filter_applied": filt,
                       "gold": {k: q[k] for k in ("gold_source_id", "gold_page", "evidence_quote", "expected_answer")},
                       "top3": hits}
                rec["eval"] = evaluate_query(q, hits)
                traces.append(rec)
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    summary = summarize(traces)
    run_info = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "libraries": {p: version(p) for p in ("chromadb", "sentence-transformers", "torch", "pypdf")},
        "embedding": {"provider": "local sentence-transformers", "model": MODEL, "dimensions": embedder.dimensions,
                      "query_prefix": "query: ", "document_prefix": "passage: ", "normalized": True},
        "vector_store": {"name": "chroma (PersistentClient)", "path": "starter/chroma_db", "metric": "cosine",
                         "search": "approximate (HNSW)"},
        "pages_loaded": len(pages), "pdf_load_seconds": round(load_s, 1),
        "strategies": STRATEGIES, "chunk_stats": stats, "cost_usd": 0,
    }
    (RESULTS / "summary.json").write_text(json.dumps({"run": run_info, "metrics": summary}, ensure_ascii=False, indent=2),
                                          encoding="utf-8")

    # Templates for manual labeling (filled by the student, not by code).
    with open(RESULTS / "manual_coherence.csv", "w", newline="", encoding="utf-8-sig") as f:
        rows = coherence_samples(pages, chunks_by_index)
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with open(RESULTS / "manual_test_audit.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["strategy", "id", "question", "filter_applied", "rank", "chunk_id", "source", "page", "chapter",
                    "section", "auto_hit", "chunk_text", "metadata_correct_0_1", "metadata_note",
                    "grounding_0_2_per_question", "grounding_reason"])
        for t in traces:
            if t["split"] != "test":
                continue
            for h in t["top3"]:
                m = h["metadata"]
                w.writerow([t["strategy"], t["id"], t["question"], json.dumps(t["filter_applied"]), h["rank"],
                            h["chunk_id"], m["source"], m["page"], m["chapter"], m["section"],
                            t["eval"]["per_rank_hit"][h["rank"] - 1], h["text"], "", "", "", ""])

    print("\n=== Retrieval (automatic) ===")
    for key, s in sorted(summary.items()):
        print(f"{key:8} Hit@1 {s['Hit@1']:>6}  Hit@3 {s['Hit@3']:>6}  page@3 {s['page_hit_at_3']}/{s['n']}  "
              f"split-suspect {s['evidence_split_suspect']}  filter {s['filter']}")
    print("\nchunks:", {k: v["chunks"] for k, v in stats.items()})
    print(f"Outputs in {RESULTS}")


if __name__ == "__main__":
    main()
