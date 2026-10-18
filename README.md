# FinSight AI

Evidence-first financial document intelligence for junior financial analysts,
using the selected FinanceBench company reports. **Current status: Phase 0
foundation only.** Retrieval, PDF processing, provider calls and Streamlit are not
implemented. The smoke command exercises synthetic contracts, not RAG quality.

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
uv run --locked pytest --basetemp=.pytest_cache/local
```

## Verification

```powershell
uv lock --check
uv sync --locked --group dev
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest
uv run --locked finsight-smoke
uv build
```

Tests use synthetic fixtures and block socket connections. Integration markers are
registered and excluded by default; explicitly use `pytest -m integration` only
after the relevant credentials and spend approval. No integration tests exist yet.
GitHub Actions runs the same foundation checks on Windows and Ubuntu with Python
3.12.15. A local pass does not establish that remote CI has run.

## Architecture and data boundaries

`src/finsight/contracts` contains Pydantic v2 models. `application.ApplicationService`
defines `answer(QueryRequest) -> Answer` for a future shared UI/benchmark service.
Configuration and application-owned redacting logging are independent of the
reserved ingestion, chunking, indexing, retrieval, context, generation, citations,
evaluation and UI packages. See [ADR 0001](docs/decisions/0001-foundation.md).

PDF page indices are zero-based; future UI page numbers must explicitly add one.
Source spans refer to unchanged extracted page text using half-open character
offsets. Contract validation checks structure, not citation support or arithmetic.
Unavailable cost, token counts and latency serialize as `null`, displayed as
`unknown`; explicit measured zero remains distinct.

Original FinanceBench files under `source-data/` are ignored and must remain
unchanged. Gold answers, rationale, quotes and annotated page locations belong
only in the offline evaluator. They must never enter retrieval, generation,
answer caches or runtime API inputs. Runtime contracts reject unknown fields.

The approved future corpus is **53 canonical filings** from AMD, American Express,
PepsiCo, Boeing, Amcor, and Johnson & Johnson. The local public sample contains
**52 matching questions across 19 filings**. All canonical filings remain in scope;
benchmark document names must not silently prefilter primary retrieval. See the
[planning audit](docs/phase-0-audit.md); this is not a completed Phase 1 manifest.

## Engineering workflow

Read [project.md](project.md) before changes. Work on a short-lived phase branch,
run the commit gates, update the [journal](docs/engineering-journal/README.md), and
stop for human review at each phase. Push, PR publication, merge and deployment
need explicit approval. Do not start a later phase from an unmerged feature branch
without approval for that arrangement.

See the [approved implementation plan](docs/superpowers/plans/2026-10-18-phase-0-foundation.md),
[prompt registry](docs/prompt-registry.csv), and [experiment conventions](docs/experiments.md).
The confirmed deadline is **2026-10-19 12:29 IST** (2026-10-18 23:59 Pacific daylight time).

## Attribution

FinanceBench: Islam et al., *FinanceBench: A New Benchmark for Financial Question
Answering* (2023), [paper](https://arxiv.org/abs/2311.11944),
[upstream dataset](https://github.com/patronus-ai/financebench). The local copied
README and original data remain under `source-data/`; this repository's MIT license
does not replace upstream data or document terms.
