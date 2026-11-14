# Corpus

| Field | Value |
|---|---|
| File | `intro-intellectual-property.pdf` (201 physical pages, 24.6 MB) |
| Title | *Introduction to Intellectual Property*, OpenStax |
| Source page | https://openstax.org/details/books/introduction-intellectual-property |
| Direct PDF | https://assets.openstax.org/oscms-prodcms/media/documents/introduction-intellectual-property_-_WEB.pdf |
| Accessed | 2026-11-14 |
| License | Creative Commons Attribution 4.0 International (CC BY 4.0): https://creativecommons.org/licenses/by/4.0/ |
| SHA-256 | `1498509864d37cb63a6ccc11bab7c783f3d30b2ed37d808ef80c56fdb676378a` |

**Attribution.** Access for free at openstax.org. Textbook content produced by OpenStax is licensed under CC BY 4.0. The book states that it is derived from material by The Michelson 20MM Foundation, with changes.

**Changes.** None. This is an unmodified copy of the PDF, redistributed here so the lab can be reproduced. Only 38 pages from chapters 3, 4 and 5 are used. The exact page list and the counting rule are in [`data/manifest.json`](../../data/manifest.json).

To check the file is the same one used in the lab, compare its SHA-256 with the value above:

```bash
certutil -hashfile starter/data/intro-intellectual-property.pdf SHA256
```

## Selected pages only

| File | Content |
|---|---|
| `selected-38-pages.pdf` (3.7 MB) | Only the 38 counted pages (chapters 3, 4, 5), copied unmodified from the full PDF |
| `selected-38-pages_page-map.csv` | Maps each page of the subset file (`new_page`) to its page in the full PDF (`original_pdf_page`) |

The pipeline, `data/manifest.json` and `benchmark/questions.json` (`gold_page`) all use the **original** page numbers of the full PDF. To find a gold page in the subset file, look it up in the page-map CSV. Rebuild both files with `python scripts/extract_selected_pages.py` (run from `starter/`).
