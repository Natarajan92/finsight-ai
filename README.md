# FinSight AI

Evidence-first financial document intelligence for junior financial analysts,
using the selected FinanceBench company reports. **Current status: Phase 2 baseline
implementation verified; real-provider acceptance blocked by an embedding timeout.** Source provenance,
fixed-token chunks, budgeted embeddings, local dense retrieval, grounded structured
generation and citation/arithmetic validation are implemented. Streamlit, alternate
retrieval arms and full evaluation remain later phases.

## Setup

Prerequisites: uv **0.12.23** and Python **3.12.15**. The Python version is selected
by `.python-version`; uv can install it if it is unavailable. Global Python
packages are not used by this project.

```powershell
uv sync --locked --group dev
uv run --locked finsight-smoke
uv run --locked finsight-rag smoke --synthetic
```

Expected smoke output (key order may differ):

```json
{"check":"synthetic_contract_roundtrip","cost_usd":"unknown","page_index":0,"status":"passed"}
```

No `.env`, API key or downloaded dataset is needed. `.env.example` documents the
optional `FINSIGHT_` settings. Paths are relative to the process working directory;
instantiate `Settings` explicitly at an application entry point.

In restricted Windows sessions, an existing global cache/temp directory may be
owned by another account. Use task-local locations without changing global settings:

```powershell
$env:UV_CACHE_DIR = Join-Path $env:TEMP 'finsight-uv-cache'
$env:UV_LINK_MODE = 'copy'
uv run --locked pytest --basetemp=.pytest-tmp
```

## Verification

```powershell
uv lock --check
uv sync --locked --group dev
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest --basetemp=.pytest-tmp
uv run --locked finsight-smoke
uv build
```

Unit tests generate tiny synthetic PDFs and block socket connections. Local-corpus
integration tests are excluded by default and require explicit source paths below.
Provider-backed tests require explicit opt-in, current verified rates, local keys
and the persistent approved spending ledger.
GitHub Actions installs pinned uv and uses `uv python install` to obtain Python
3.12.15 on Windows and Ubuntu. CI test scratch space is under the existing runner
temp directory; a fresh checkout does not need a pre-existing pytest cache.
A local pass does not establish that remote CI has run.

## Architecture and data boundaries

`src/finsight/contracts` contains Pydantic v2 models. `application.ApplicationService`
defines `answer(QueryRequest) -> Answer` for the shared baseline service and future UI.
Configuration and application-owned redacting logging are independent of the
ingestion and offline evaluation modules. LangChain composes retrieval, bounded
context, native Claude drafts and application-owned validation. See
[ADR 0001](docs/decisions/0001-foundation.md) and
[ADR 0002](docs/decisions/0002-dataset-provenance.md) and
[ADR 0003](docs/decisions/0003-baseline-rag.md).

PDF page indices are zero-based; future UI page numbers must explicitly add one.
Source spans refer to unchanged extracted page text using half-open character
offsets. Contract validation checks structure, not citation support or arithmetic.
Unavailable cost, token counts and latency serialize as `null`, displayed as
`unknown`; explicit measured zero remains distinct.

Original FinanceBench files under `source-data/` are ignored and must remain
unchanged. Gold answers, rationale, quotes and annotated page locations belong
only in the offline evaluator. They must never enter retrieval, generation,
answer caches or runtime API inputs. Runtime contracts reject unknown fields.

The approved corpus is **53 canonical filings / 9,504 PDF pages** from AMD, American Express,
PepsiCo, Boeing, Amcor, and Johnson & Johnson. The local public sample contains
**52 matching questions across 19 filings**. All canonical filings remain in scope;
benchmark document names must not silently prefilter primary retrieval. See the
[Phase 1 audit](docs/data_audit.md) for verified counts, hashes, extraction gaps,
and split distribution.

## Local source preparation

Keep original PDFs in `source-data/pdfs/` and the two upstream JSONL files in
`source-data/data/`. Originals and generated page caches stay ignored. The checked-in
manifest stores portable relative paths, hashes, and provenance; it contains no
benchmark question text or annotations.

```powershell
uv run --locked finsight-ingest manifest --metadata source-data/data/financebench_document_information.jsonl --pdf-root source-data/pdfs --output data/manifests/financebench-selected.json
uv run --locked finsight-ingest extract --manifest data/manifests/financebench-selected.json --pdf-root source-data/pdfs --cache-root data/cache/pages
uv run --locked finsight-benchmark-audit split --questions source-data/data/financebench_open_source.jsonl --manifest data/manifests/financebench-selected.json --policy configs/evaluation/split-policy.json --output-dir configs/evaluation
uv run --locked finsight-benchmark-audit validate --questions source-data/data/financebench_open_source.jsonl --manifest data/manifests/financebench-selected.json --split-dir configs/evaluation --split development --cache-root data/cache/pages
```

Re-running preparation is idempotent. A different source manifest or frozen split
is refused; review a new dataset/split version instead of overwriting it. Cache
identity includes the source hash, extraction configuration, and parser/backend
versions. Corrupt/stale caches rebuild from the verified PDF. Extractor `phase1-v3`
flags image content without extractable text; no OCR or table-cell reconstruction
runs. Nine scanned Amcor appendix pages remain documented text-coverage gaps.
Repaired PDFs, native syntax errors, and unknown warnings fail validation. The
specific ActualText-position warning preserves available text with an explicit
possible-loss diagnostic (618 pages); those pages are not certified complete.
Password-required and
unknown encrypted PDFs are rejected. P1-006 approves only the nine exact hashes
for American Express 2022 and Boeing 2015-2022, which open without passwords and
permit copying; manifest and page diagnostics disclose this exception. Original
files are never decrypted or rewritten. Benchmark validation recomputes the
declared split policy before producing development feedback.

To verify local sources and cached pages without provider calls:

```powershell
$env:FINSIGHT_SOURCE_PDF_DIR = 'source-data/pdfs'
$env:FINSIGHT_BENCHMARK_DIR = 'source-data/data'
uv run --locked pytest -m integration tests/test_corpus_integration.py --basetemp=.pytest-tmp
```

The frozen split is **36 development / 16 holdout**, seed **42**, with all six
companies represented in both. Tune only on development. Holdout runs once after
all four A/B/C/D configurations are frozen in a later phase. The same filings may
appear in both splits: this evaluates unseen questions, not unseen documents.
The same 53 original PDF filings remain the knowledge corpus for every arm.
FinanceBench question-answer JSON is never an embedding input. Reference answers,
justifications, evidence passages, and page labels never enter generation prompts.
The shared service will receive question text only, plus fair explicit filters.

## Engineering workflow

Read [project.md](project.md) before changes. Work on a short-lived phase branch,
run the commit gates, update the [journal](docs/engineering-journal/README.md), and
stop for human review at each phase. Push, PR publication, merge and deployment
need explicit approval. Do not start a later phase from an unmerged feature branch
without approval for that arrangement.

See the [Phase 1 plan](docs/superpowers/plans/2026-10-18-phase-1-ingestion.md),
[prompt registry](docs/prompt-registry.csv), and [experiment conventions](docs/experiments.md).
The confirmed deadline is **2026-10-19 12:29 IST** (2026-10-18 23:59 Pacific daylight time).

## Attribution

FinanceBench: Islam et al., *FinanceBench: A New Benchmark for Financial Question
Answering* (2023), [paper](https://arxiv.org/abs/2311.11944),
[upstream dataset](https://github.com/patronus-ai/financebench). The local copied
README and original data remain under `source-data/`; this repository's MIT license
does not replace upstream data or document terms.

PyMuPDF **1.28.2** and MuPDF **1.28.2** are used for source extraction and rendering.
See their [official license notice](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright).
The human approved this dependency for the project; the repository license is unchanged.

## Baseline RAG commands

Configure `FINSIGHT_NEBIUS_API_KEY` and `FINSIGHT_ANTHROPIC_API_KEY` in the ignored
`.env`. No OpenAI API account is required. The configured models are Nebius
`Qwen/Qwen3-Embedding-8B` and Claude `claude-sonnet-5`; unavailable models fail
explicitly rather than switching providers/models.

```powershell
uv run --locked finsight-rag prepare-tokenizer --config configs/runtime/phase-2-baseline.json
# Run once for a new approved ledger; never reset an existing budget:
uv run --locked finsight-rag budget-init --ledger data/cache/budget/testing.sqlite3
uv run --locked finsight-rag preflight --config configs/runtime/phase-2-baseline.json
uv run --locked finsight-rag build-index --config configs/runtime/phase-2-baseline.json --allow-paid
uv run --locked finsight-rag ask --config configs/runtime/phase-2-baseline.json --question "What was AMD revenue in 2022?" --allow-paid
```

Before preflight, create the ignored `data/cache/budget/rates.json` with the
`RateBook` contract: schema version `1` and two cards containing provider, exact
model ID, `service_tier: default`, verified input/output USD per million tokens,
official `source_url` and an aware UTC `verified_at`. Rates older than 24 hours
block dispatch. Use the [official Nebius catalog](https://tokenfactory.nebius.com/api/public/models_info)
and [Claude pricing](https://platform.claude.com/docs/en/about-claude/pricing).
Never copy a historical result snapshot as a current rate verification.

The shared test ceiling is $5, with $4 working and $1 untouched reserve. Phase 2
has a $0.75 sublimit including indexing, retries and queries. Preflight estimates
all uncached embedding inputs and four conservative queries with eligible retries;
a conflict stops the build. Unknown timeout billing stays reserved. Keep the ledger,
identity marker, `results/testing-budget-identity.json`, caches and campaign
receipts; missing/corrupt storage fails closed. The independent authority binds
the testing budget to one ledger path. Moving it or losing budget files requires
reconciling prior activity; another `--ledger` path cannot create a new allowance.

Defaults use the existing manifest/PDF/page-cache paths. Override with `--manifest`,
`--pdf-root`, `--page-cache`, `--tokenizer-dir`, `--embedding-cache`, `--index-root`,
`--rates`, `--ledger`, `--trace-root`, and `--env-file`. Use absolute paths when
running from another cwd. Generated indexes live below the config fingerprint.
`ask` prints an `answer`/`trace_id` JSON envelope; exit 0 includes explicit
abstentions, 1 means an operational error, and argparse uses 2 for invalid arguments.

Real acceptance is a single campaign executor; it never supplies gold-derived
filters and replays completed matching records without purchasing more answers:

```powershell
$env:FINSIGHT_SOURCE_PDF_DIR = (Resolve-Path source-data/pdfs).Path
$env:FINSIGHT_BENCHMARK_DIR = (Resolve-Path source-data/data).Path
$env:FINSIGHT_RAG_PAID_TESTS = '1'
uv run --locked pytest -m integration tests/test_rag_integration.py --basetemp=.pytest-tmp/p2-real -q
```

Without the paid flag, provider tests explicitly skip. With it, missing credentials,
rates, source identity or a completed index fail acceptance. Interrupted started
campaigns require inspection and cannot silently repurchase requests. See the
[acceptance summary](results/phase-2-baseline-smoke.md) and
[local review checkpoint](docs/reviews/phase-2.md). Citation containment is distinct
from semantic support; the latency/faithfulness targets remain unproven by smoke tests.

Full-corpus embedding is a bulk job: `FINSIGHT_INDEX_JOB_TIMEOUT_S` defaults to 14400
seconds (maximum four hours). Each batch retains its 45-second context and each
physical attempt its 20-second timeout. Answer requests retain a total 45-second
deadline. Completed batches persist for compatible resumption; elapsed bulk time
does not authorize extra spending.

Elapsed limits bound client waits as well as transport operations. They cannot
prove that a provider stopped processing a timed-out request. Late results cannot
populate caches or terminal records, and the complete uncertain reservation stays
charged against available testing funds. Sixteen unfinished calls block further
dispatch until resources return.

Index integrity uses exact hash-verified canonical float32 references plus a
`1e-6` L2 tolerance for Chroma cosine renormalization. Preserve the generated
`vector-references/` directory with its index; missing references fail closed.

The current real build retains 1,792 of 22,070 chunk vectors. Its uncertain timeout
reservation remains held; the development answer campaign has not run. Review the
[acceptance/recovery record](results/phase-2-baseline-smoke.md) before explicitly
resuming paid work. Phase 2 is incomplete until that exit gate passes.
