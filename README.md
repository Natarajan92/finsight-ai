# FinSight AI

Evidence-first financial document intelligence for junior financial analysts,
using the selected FinanceBench company reports. **Current status: Phase 1
dataset and provenance.** Source manifests, PDF extraction/cache, and offline
benchmark preparation are implemented. Retrieval, generation, and Streamlit are
later phases. The smoke command exercises synthetic contracts, not RAG quality.

## Setup

Prerequisites: uv **0.12.23** and Python **3.12.15**. The Python version is selected
by `.python-version`; uv can install it if it is unavailable. Global Python
packages are not used by this project.

```powershell
uv sync --locked --group dev
uv run --locked finsight-smoke
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
Provider-backed tests, when introduced, require separate credentials/spend approval.
GitHub Actions installs pinned uv and uses `uv python install` to obtain Python
3.12.15 on Windows and Ubuntu. CI test scratch space is under the existing runner
temp directory; a fresh checkout does not need a pre-existing pytest cache.
A local pass does not establish that remote CI has run.

## Architecture and data boundaries

`src/finsight/contracts` contains Pydantic v2 models. `application.ApplicationService`
defines `answer(QueryRequest) -> Answer` for a future shared UI/benchmark service.
Configuration and application-owned redacting logging are independent of the
ingestion and offline evaluation modules. Chunking, indexing, retrieval, context,
generation, citations, and UI remain boundaries for later phases. See
[ADR 0001](docs/decisions/0001-foundation.md) and
[ADR 0002](docs/decisions/0002-dataset-provenance.md).

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
versions. Corrupt/stale caches rebuild from the verified PDF. Extractor `phase1-v2`
flags image content without extractable text; no OCR or table-cell reconstruction
runs. Nine scanned Amcor appendix pages remain documented text-coverage gaps.

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
