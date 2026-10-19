# AMD application verification — 2026-10-19 IST

The delivered slice is a Streamlit RAG app over **AMD_2022_10K**, with 121 PDF
pages and 313 fixed-token chunks. It uses the existing shared application service,
source checks, Nebius embeddings, Claude generation, citation validation and budget.
The original six-company benchmark and four-arm evaluation remain incomplete.

## Observed live result

- Question: `What was AMD revenue in 2022?`
- Outcome: `answered`, with one source citation on **PDF page 54**.
- Answer: AMD net revenue was $23,601 million, approximately $23.6 billion.
- Citation quote: `Net revenue` followed by `$` and `23,601` on separate extracted lines.
- Source: [AMD 2022 Form 10-K, PDF page 54](https://ir.amd.com/sec-filings/content/0000002488-23-000047/0000002488-23-000047.pdf#page=54).
- Trace: `e4f3041e44234916836ce2eaaee4b7df`.
- Usage: 5,291 input tokens, 140 output tokens, one generation and one query embedding.
- Usage-priced cost: **$0.01191832**. Ledger increase: $0.011919, including rounding.
- Answer-service latency: **9,282 ms**. This is one observation, not a median or
  a demonstration of the <8-second median target or claim-faithfulness target.

Source fingerprint:
`723a5092e7ad3aa96c406c9d81e63c0cbb8b2990a64772b2aba3a090fe83b5f3`.
Index fingerprint:
`6721d3b1fc5ad652d5d910862ac1785ba03fd6df5e0d9bf02cba745008018a62`.

A fresh workspace reopened the identical answer with live calls disabled and
the paid-application factory replaced by a function that raises. No second
purchase occurred. The real Streamlit entry point also passed an AppTest check:
initial live switch off, free saved answer, literal dollar amounts, citation
PDF page 54, browsing PDF page 94 and rerun. Paid-client creation was forbidden.

After the live check, the existing ledger showed accounted **$0.030903**, uncertain
reservation **$0.000065**, working availability **$3.969032** and untouched **$1**
reserve. No allowance was reset or increased. New AMD answers use the existing
atomic Phase 3 sublimit of $0.75. Original uncertain reservations remain held.

## Verification

| Check | Observed result |
|---|---|
| App/factory/contracts focused suite after review fixes | 72 passed |
| Full current source with committed notebook in an isolated snapshot | 357 passed, one host symlink skip, seven opt-in integration deselections; 64.41 s |
| Ruff lint and formatting on that snapshot | Passed, 156 formatted files |
| `uv lock --check` | Passed, 152 locked packages |
| `uv build` | Wheel and sdist built |
| Build contents | UI included; no .env, source PDFs, budget authority or generated caches |
| `finsight-smoke` | Passed |
| `finsight-rag smoke --synthetic` | Passed, zero provider calls |
| Real AMD offline index and source | 121 pages, 313 chunks verified |
| Local Streamlit HTTP health | HTTP 200, `ok` |
| Visual browser inspection | Unavailable: no browser surface connected |

The **unmodified local notebook is intentionally executed**, so running the full
suite directly in this checkout still reports
`test_notebook_is_unexecuted_and_every_code_cell_compiles` as failed and seven
walkthrough fixture errors. The earlier direct run had 346 passes, one skip,
seven deselections, that failure and those seven errors. The successful snapshot
used the exact committed notebook bytes with the current application/test files;
the user's notebook was never cleared, rewritten or staged. Its SHA-256 remains
`64dc03cb22254a2ff0b5817ff2420b34862ea94f30fc0556d678f7e75530c799`.

The first snapshot used a long scratch path and hit Windows vector-file rename
errors. Repeating with short `.pytest-tmp/amd-shipped` resolved those environmental
failures without weakening tests. Sandbox-account access to the pre-existing
tokenizer directory required an elevated read; the user's cache permissions and
all artifact identities were preserved.

Independent review found two issues, each reproduced with a failing regression:
currency was interpreted as Markdown math, and session reruns could display an
answer without rechecking its receipt. Literal text rendering and free replay
validation fixed both. A separate serializer regression fixed the Decimal zero
default in token-count traces. No additional blocking review findings remained.

## Run

```powershell
uv run --locked streamlit run streamlit_app.py
```

Open http://127.0.0.1:8501. Existing sources/index/receipts are local ignored
artifacts; a fresh checkout needs the setup described in the README. No push,
merge, deployment or full-corpus benchmark was performed.
