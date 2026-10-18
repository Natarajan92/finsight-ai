# Phase 1 data and provenance audit

Recorded 2026-10-18, IST. This is a source/preparation audit, not a RAG evaluation.
Original FinanceBench files were not modified. Runtime knowledge is restricted to
original PDF content; benchmark annotations remain offline evaluation inputs.

## Corpus and question coverage

| Company | Local PDFs | Canonical filings | PDF pages | Questions | Development | Holdout |
|---|---:|---:|---:|---:|---:|---:|
| AMD | 9 | 9 | 1,431 | 8 | 5 | 3 |
| American Express | 1 | 1 | 260 | 7 | 5 | 2 |
| PepsiCo | 13 | 13 | 4,231 | 11 | 8 | 3 |
| Boeing | 8 | 8 | 1,347 | 8 | 6 | 2 |
| Amcor | 11 | 9 | 1,094 | 9 | 6 | 3 |
| Johnson & Johnson | 13 | 13 | 1,141 | 9 | 6 | 3 |
| **Total** | **55** | **53** | **9,504** | **52** | **36** | **16** |

All required question-linked filings exist. Questions link to 19 filings; all 53
canonical filings remain the common corpus. Two unmatched Amcor files are
byte-identical aliases of uniquely metadata-matched filings and are excluded from
the manifest without deleting their originals. The complete metadata file contains
a conflicting duplicate Foot Locker record outside this corpus; the loader reports
it and rejects unresolved selected-company conflicts.

Document information is joined using its actual `doc_name`, `company`, `doc_type`,
`doc_period`, and `doc_link` fields. `gics_sector` is accepted as source metadata,
not guessed or embedded. Source filing-type case is preserved. Periods below are
the metadata's year values; no quarter/month precision is inferred from filenames.

| Company | Filing types and counts | Metadata years and counts |
|---|---|---|
| AMD | `10k`: 8; `10k_annualreport`: 1 | 2015-2021: 1 each; 2022: 2 |
| American Express | `10k`: 1 | 2022: 1 |
| PepsiCo | `10k`: 8; `Earnings`: 3; `8k`: 2 | 2015-2021: 1 each; 2022: 2; 2023: 4 |
| Boeing | `10k`: 8 | 2015-2022: 1 each |
| Amcor | `10k`: 5; `8k`: 2; `10q`: 1; `Earnings`: 1 | 2019-2021: 1 each; 2022: 3; 2023: 3 |
| Johnson & Johnson | `10k`: 8; `Earnings`: 3; `8k`: 2 | 2015-2021: 1 each; 2022: 2; 2023: 4 |

## Extraction and coverage limitations

Pinned Python 3.12.15 / PyMuPDF 1.28.2 / MuPDF 1.28.2; explicit original-order
`TEXTFLAGS_TEXT` extraction. Raw text is retained without normalization. Blocks
carry bounding boxes and exact half-open source spans validated against the page.
Cached data is validated for source/config/parser identity, page order/completeness,
and payload integrity before reuse; interrupted writes use atomic replacement.

- **9,504 page records:** 9,486 nonempty, 18 text-empty, zero parser errors, zero
  block-mapping failures.
- Nine owner-encrypted originals (American Express 2022; Boeing 2015-2022) open
  without passwords and permit copying. P1-006 approves only their exact hashes.
  Manifest diagnostics identify all nine; 1,607 page records disclose readable
  encryption. Password-required, unknown encrypted, repaired, native syntax-error,
  and unknown-warning sources fail validation. Originals remain unchanged; no
  decryption is performed.
- **618 pages in nine filings** emit the specific native ActualText-position
  warning, indicating possible lost or mispositioned text. Available raw text is
  preserved and flagged `actualtext_position_warning`; `ok` means nonempty extraction,
  not complete semantic coverage. No warning is silently discarded. No extraction
  flags or text were changed to silence these warnings; all other warnings fail.
- Visual review of all 18 text-empty pages found **nine blank pages and nine
  scanned Amcor 2020 appendix pages** containing deferred-compensation amendments.
  `phase1-v3` retains `image_content_without_text` diagnostics for the nine image-only
  pages. They remain in the manifest/cache as explicit coverage gaps. OCR is not
  implemented, and these pages cannot support text retrieval yet.
- Every one of the 59 annotated evidence references has a valid zero-based page
  index and nonempty extracted text. None targets the text-empty pages. This is
  a structural source check, not holdout answer/retrieval scoring.
- Six development financial-table pages, one per company, were visually compared
  with original PDF renders. Reviewed AMD and PepsiCo cash-flow statements,
  American Express summary performance, Boeing financial position, Amcor
  earnings reconciliation, and Johnson & Johnson earnings/regional sales.
  Sampled years, headings, scales, negatives, footnotes, and values are retained.
  Column relationships remain flattened text plus geometry; no table-cell model
  or general table-semantic correctness claim is made.
- A terminal preview showed replacement glyphs. A direct Unicode audit found
  **zero U+FFFD characters** in all extracted pages; nonbreaking spaces, em/en
  dashes, and curly punctuation are present in the stored text. The issue was
  Windows terminal decoding, so no speculative source normalization was applied.
  Default flags use character IDs for unknown Unicode; zero U+FFFD therefore does
  not independently prove correct character decoding or complete text coverage.

Development-only annotation diagnostics contain **41 references, 17 exact matches**
after Unicode NFKC/case/whitespace normalization, and 24 nonmatches. Matching is a
mechanical extraction diagnostic; nonmatches can reflect extraction order or
annotation formatting and do not establish wrong answers or incorrect annotations.
The earlier pre-split 23/59 diagnostic is historical; no new holdout quote feedback
is produced. Detailed case IDs/page annotations and local QA renders remain under
ignored `data/evaluation/`, outside runtime inputs and public summaries.

## Frozen questions and reasoning coverage

Seed **42**, algorithm **`company-reasoning-v1`**. Company quotas use largest
remainder with a stable company-name tie-break. Constrained reasoning allocation
maximizes feasible coverage before minimizing within-company proportional error;
seeded SHA-256 ordering chooses IDs without using answers, justifications, evidence,
or model performance. Original string IDs are preserved in separate
[development](../configs/evaluation/development.json) and
[holdout](../configs/evaluation/holdout.json) manifests.

| Original reasoning label | Total | Development | Holdout |
|---|---:|---:|---:|
| Information extraction | 12 | 8 | 4 |
| Information extraction OR Logical reasoning | 1 | 1 | 0 |
| Information extraction OR Logical reasoning OR | 1 | 1 | 0 |
| Logical reasoning (based on numerical reasoning) | 2 | 1 | 1 |
| Logical reasoning (based on numerical reasoning) OR Logical reasoning | 1 | 1 | 0 |
| Logical reasoning (based on numerical reasoning) OR Numerical reasoning OR Logical reasoning | 3 | 2 | 1 |
| Numerical reasoning | 5 | 3 | 2 |
| Numerical reasoning OR Logical reasoning | 2 | 1 | 1 |
| Numerical reasoning OR information extraction | 3 | 2 | 1 |
| Missing (`null`) | 22 | 16 | 6 |

All six companies and all seven repeated reasoning categories, including missing,
appear in both splits. Three singleton labels cannot appear in both. Twelve of
13 repeated company/reasoning strata appear in both; Boeing's two information
extraction questions are both in development under the constrained optimum.
Source-order reversal reproduces the same IDs/fingerprints. A different existing
frozen split cannot be overwritten by preparation commands.
Validation also recomputes the policy before development feedback, rejecting
checksum-consistent altered membership. The real and synthetic split fingerprints
are pinned in tests; algorithm and original memberships are unchanged.

Development questions reference 17 filings and holdout questions 10, with **eight
filings shared**. **The same filings may appear in both splits: this evaluates
unseen questions, not unseen documents.** The sample is small and uneven; future
metrics must disclose that limitation.

Tune prompts and retrieval only on development. Freeze the corpus, source/index
revisions, chunking, embedding model, reranker, generation model, prompt, candidate
count, context budget, seed, and filters before one final holdout campaign. A/B/C/D
must use identical question sets and full-corpus scope; paired rerank arms reuse
the same pre-rank pools. No holdout RAG evaluation, embeddings, model calls,
accuracy, faithfulness, or latency measurements have run in Phase 1.

## Fingerprints and immutability

| Artifact | SHA-256 |
|---|---|
| Canonical 53-source fingerprint | `7376d03d8183077b92ed98b8c4e3a584fefd02202b75feba82cdc13b2519fad3` |
| Original 55-PDF audit aggregate | `7d8ca4d2d901038058ac345778ecb5898f20e04e6f5a0c97ffd344db41a776fe` |
| Question JSONL | `a5a2aa673e573e55675fc3c0f9aa38c1cf59d2abc91edb077534f71f10a71877` |
| Metadata JSONL | `1c69127783879de8cdadb159d2181f39bc3123b8e0ebf74031c3969d69189575` |
| Shared split fingerprint | `e6ec481633654b779721f1d94c7aa05a65e43c9f37deae177819658d2b665431` |

The 53-source fingerprint hashes canonical JSON of sorted name/hash pairs. The
historical 55-PDF aggregate hashes sorted `stem:hash` lines with no trailing
newline. They intentionally describe different selections/serializations.
All 55 original selected PDF hashes and both JSONL hashes equal their before-work
snapshot and Phase 0 baselines. There is no index fingerprint: no index exists.

## Verification record

See [P1-004](engineering-journal/phase-01.md#p1-004---approved-phase-1-implementation)
for exact commands, test counts, failed hypotheses, and corrections. Unit tests use
synthetic fixtures and block sockets; local integration tests verify source hashes,
all cached pages without reparsing, benchmark joins, and frozen split reproduction.
Fresh isolated wheel verification covers all 19 exported contract schemas, runtime
imports, synthetic smoke, and both installed CLI entry points from an empty cwd.
Phase 1 GitHub Actions remains unexecuted until an approved push.

Independent review and correction evidence are in
[P1-005](engineering-journal/phase-01.md#p1-005---independent-branch-review) and the
[review checkpoint](reviews/phase-1.md). One Minor finding remains deferred:
unmatched nonalias PDFs lack an explicit diagnostic. Metadata controls corpus
membership; this does not authorize adding those sources.
