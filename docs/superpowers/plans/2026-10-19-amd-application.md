# AMD Application Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan
> in this session. User authorized judgment and execution; preserve the existing
> checkout and local experiments. One independent review at the end.

**Goal:** A usable AMD financial-document RAG app with inspectable citations.

**Architecture:** Streamlit calls an AMD workspace facade, which delegates answers
to the existing shared application service via the scoped experiment lab. Durable
receipts prevent duplicate purchases and bind replay to unchanged evidence.

**Tech Stack:** Python 3.12, Streamlit 1.65.0, Pydantic, existing LangChain/Chroma.

**Spec:** `docs/superpowers/specs/2026-10-19-amd-application-design.md`.

## Global constraints

- AMD_2022_10K only; no benchmark labels at runtime.
- Existing $5 ceiling, $4 working funds, $1 reserve and $0.75 phase 3 limit.
- Preserve notebook SHA-256 64dc03cb22254a2ff0b5817ff2420b34862ea94f30fc0556d678f7e75530c799.
- No push/merge/deploy; no original PDF, manifest or split edits.
- Use current checkout: the prior approved execution explicitly retained it.

## Review focus

- Streamlit reruns must not cause purchases or keep mutable provider clients shared.
- Interrupted requests and tampered receipts must fail closed before dispatch.
- Page labels must add one exactly once; quoted evidence must match the source.
- Invalid or cross-company scope must fail before purchasing generation.
- Setup/provider failures must produce safe useful messages without raw secrets.

### Task 1: Durable scoped answers

**Files:** `src/finsight/runtime/experiment_pilot.py`, `tests/rag/test_amd_app.py`.
**Interfaces:** `ask_pilot(lab, request, arm, *, allow_paid=False) -> dict` returns
answer JSON, trace ID, replay flag and arm. It accepts only the AMD document lab,
uses `lab.application(arm).answer(request)`, and stores receipts under trace_root.

- [x] Add failing tests for default-off spending, scoped answers, replay,
  interrupted/uncertain requests, changed evidence/config and tampered receipts.
- [x] Run focused tests; confirm failures identify missing implementation.
- [x] Implement atomic started/completed receipts with source/index/config/request
  identity, citation revalidation, safe errors and resource ownership by the lab.
- [x] Run focused tests and existing experiment factory tests; record results.

### Task 2: AMD workspace and Streamlit presentation

**Files:** `src/finsight/ui/workspace.py`, `src/finsight/ui/app.py`,
`src/finsight/ui/__init__.py`, `streamlit_app.py`, `.streamlit/config.toml`,
`tests/rag/test_amd_app.py`, `pyproject.toml`, `uv.lock`.
**Interfaces:** `AmdWorkspace` opens/validates the existing source/index offline,
provides metadata, `page(number)` and `ask(question, *, allow_paid=False)` and
closes owned resources. `render(workspace)` draws the actual app and can be run by
Streamlit AppTest against a synthetic PDF and the real service boundary.

- [x] Add failing tests for metadata, explicit AMD query scope, citation pages,
  no-request startup/rerun, guarded submission, replay, abstention and safe errors.
- [x] Implement workspace and form-based question UI with source tab, evidence
  quotes, actual/unknown usage, result download and explicit live switch.
- [x] Pin/install Streamlit; run focused real AppTest checks with sockets blocked.

### Task 3: Verify and document the application

**Files:** `README.md`, `docs/engineering-journal/amd-application.md`,
`results/amd-application-smoke.md`.

- [x] Open actual AMD index offline, inspect pages and existing budget.
- [x] Run one bounded live question and repeat offline to prove receipt replay.
- [x] Run full keyless suite (report executed local notebook separately), Ruff,
  lock verification, build and synthetic smoke. Verify original notebook hash.
- [x] Start Streamlit, inspect its real AppTest/source workflow and HTTP health;
  keep local app available. Browser surface unavailable, recorded in verification.
- [x] Obtain independent review, fix important findings with regressions, record
  actual checks, usage, limitations and exact launch command. Leave changes local.
