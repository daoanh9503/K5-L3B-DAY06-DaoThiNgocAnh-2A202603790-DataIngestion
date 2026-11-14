# Benchmark

- `questions.json`: 20 questions, 15 dev (q01–q15) / 5 test (q16–q20), fixed before running the pipeline.
- Fields: `id, split, type, question, expected_answer, gold_source_id, gold_page, evidence_quote, filter`.
- `gold_page` = 1-based physical PDF page index (not the printed page number).
- Filter questions: q02 (chapter 3), q13 (chapter 4), q15 (chapter 5) in dev; q20 (chapter 5) in test. Filters model user-provided context given before retrieval; gold answers/sources are never put in queries or filters.
- Evidence check: `python scripts/verify_benchmark.py` (from `starter/`) confirms each quote is on its gold page; the author also checked each in the PDF.
- Questions were drafted with AI assistance (Claude) and reviewed by the author.

## Strategy selection criterion (fixed before reading test results)

1. Evidence Hit@3 on **dev**
2. Chunk coherence (manual, /2)
3. Resources (chunk count, embedding time)

## Known risks

- Dev and test come from the same book; test is skewed to chapter 5 (4/5) and has no chapter-3 question.
- Small test set (5): differences of 1–2 questions are not significant.
