---
name: bibtex-export
description: Export filed papers as a clean BibTeX bibliography. Use when asked for a .bib, a bibliography, or citations to paste into a paper.
---

# BibTeX Export Skill

Assemble a bibliography from papers already in `/memories/library/`.

## Steps
1. Read the relevant topic file(s) under `/memories/library/`.
2. Pull the `@misc{...}` records; drop the `% note:` lines.
3. De-duplicate by citation key and by arXiv `eprint` id.
4. Sort by year (newest first), then first author.

## Output
- A single fenced ```bibtex block, nothing else before it.
- Consistent keys: `lastname_year_keyword`.
- Every entry must have `title`, `author`, `year`, `eprint`, `archivePrefix`,
  `primaryClass`, `url`. If a field is missing, fetch it with `get_arxiv_paper`.
