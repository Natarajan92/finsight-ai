# Phase 0 planning audit: selected FinanceBench coverage

Read-only audit on 2026-10-18, before implementation, by Codex. This is planning
evidence, not a Phase 1 extraction/manifest deliverable. No labels or source text
are copied into runtime artifacts.

| Company | Local PDFs | Canonical metadata filings | Questions | Question filings | Canonical pages |
|---|---:|---:|---:|---:|---:|
| AMD | 9 | 9 | 8 | 2 | 1,431 |
| American Express | 1 | 1 | 7 | 1 | 260 |
| PepsiCo | 13 | 13 | 11 | 5 | 4,231 |
| Boeing | 8 | 8 | 8 | 2 | 1,347 |
| Amcor | 11 | 9 | 9 | 5 | 1,094 |
| Johnson & Johnson | 13 | 13 | 9 | 4 | 1,141 |
| Total | 55 | 53 | 52 | 19 | 9,504 |

The complete local download contains 368 PDFs (705,172,379 bytes), 150 unique
questions, and 361 metadata rows representing 360 unique document names. Every
metadata document and question document has a corresponding exact local PDF.
The selected canonical PDFs occupy 92,168,913 bytes. Question types: 6
metrics-generated, 24 domain-relevant, 22 novel-generated. Coverage is uneven;
American Express has only one filing. There are enough real questions to avoid
expanding the company scope; the human selected all 53 canonical filings.

All 55 selected-company PDFs opened with PyMuPDF 1.28.2. The two unjoined Amcor
aliases have byte-identical hashes to their `_dated-` canonical documents:

- `AMCOR_2022_8K_2022-04-26` / `AMCOR_2022_8K_dated-2022-04-26`:
  `adddeda2984e18100c35996823a2f4ec09107c7e0e8c2515a9ebd76b15773c2a`
- `AMCOR_2022_8K_2022-07-01` / `AMCOR_2022_8K_dated-2022-07-01`:
  `1de32e72c265486469f3b1c7cbfbe064a27055e60f7b43a81439986dda9025ad`

Keep both originals intact. Future manifest selection excludes the two aliases.
Seven PepsiCo annual PDFs have over 400 pages; parsing cost and table order need
attention without trimming the corpus based on gold annotations.

## Actual annotation schema and evidence diagnostics

- Question IDs are strings, not the integer described in the copied README.
- Evidence keys: `doc_name`, `evidence_page_num`, `evidence_text`,
  `evidence_text_full_page`; pages are zero-indexed integers.
- Metadata keys include `gics_sector`; filing-type values have mixed case.
- Reasoning/justification/domain fields can be null; 28 selected justifications
  are null. No selected question evidence points to a different filing.
- Global metadata has two conflicting rows for `FOOTLOCKER_2023_annualreport`,
  differing in `doc_period` (2023 vs 2022), outside the selected companies.
  Future code must flag conflicts instead of silently overwriting a dictionary.

Selected cases contain 59 references across 49 unique PDF pages in 19 documents.
All referenced pages exist and contain extracted text. Exact evidence substring
matching after NFKC/case/whitespace normalization succeeded for 23/59 references;
sorting PDF text reduced this to 19/59. None had less than 50% unique token overlap.
These are mechanical diagnostics, not correctness, support or faithfulness scores.
Table ordering/annotation formatting requires Phase 1 review; do not repair it by
injecting annotated evidence into extracted pages, chunks, prompts or indexes.

## Fingerprints and method

Original annotation file SHA-256:

- `financebench_open_source.jsonl`:
  `a5a2aa673e573e55675fc3c0f9aa38c1cf59d2abc91edb077534f71f10a71877`
- `financebench_document_information.jsonl`:
  `1c69127783879de8cdadb159d2181f39bc3123b8e0ebf74031c3969d69189575`

All 55 selected-company PDF fingerprint:
`7d8ca4d2d901038058ac345778ecb5898f20e04e6f5a0c97ffd344db41a776fe`.
It is SHA-256 of UTF-8 sorted `stem:sha256` entries joined by newline, without a
trailing newline. It includes aliases and is **not** a future index/split fingerprint.

The audit used inline read-only Python with `json.loads` per nonempty line,
exact metadata/PDF stem joins, `hashlib.sha256`, and `pymupdf.open`/page text.
Raw evidence/answers remained in memory only; no extraction cache/index was created.
Diagnostic scripts initially assumed the README's evidence key, then corrected
to actual `doc_name`. Output aggregation also needed tuple-key serialization and
integer-length corrections. Failed probes were not counted as completed validation.
Hash comparisons after inspection confirmed both JSONLs and selected PDFs unchanged.

## Environment baseline

Only README/LICENSE were tracked at main SHA `75461c0`; project instructions,
templates and source-data were untracked. Main matched the live remote. Connected
GitHub repository is public, with usable permissions and no open PRs; protection
was not verified. No global Git settings were changed.

Global Python 3.10.10 has Pydantic 1.10.11, old SDK/UI packages, no pytest/Ruff,
and seven reported `pip check` conflicts. Installed Python 3.12.15 works.
`uv pip install --dry-run` against the managed interpreter was rejected by the
externally-managed-environment guard; no override was used. Standalone
`uv pip compile --python ... --python-platform x86_64-pc-windows-msvc
--only-binary :all: --cache-dir ... -` resolved 14 foundation dependencies, and
uv-build 0.12.23 resolved separately. No packages were installed during planning.

ContextHub's PowerShell launcher was blocked by script execution policy; the
installed `.cmd` launcher worked. Default registry/uv caches were not writable.
`CHUB_DIR`/`UV_CACHE_DIR` temporary cache overrides worked without global changes.
