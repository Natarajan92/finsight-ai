# Phase 2 baseline acceptance

Status: **Phase 2 incomplete.** Product implementation and review corrections are
verified at `593ca53`. The full-corpus build stopped on `provider_timeout` under
the approved 20-second wait limit. Completed vectors and unknown billing are
preserved; no automatic retry or development answer campaign followed.

## Frozen inputs

- Corpus: 53 canonical filings / 9504 pages.
- Source fingerprint: `7376d03d8183077b92ed98b8c4e3a584fefd02202b75feba82cdc13b2519fad3`.
- Split: seed 42, 36 development / 16 holdout.
- Split fingerprint: `e6ec481633654b779721f1d94c7aa05a65e43c9f37deae177819658d2b665431`.
- Scenario: fixed/dense/no rerank; native model IDs remain unchanged.

## Preflight evidence

Free account metadata confirmed `Qwen/Qwen3-Embedding-8B` and `claude-sonnet-5`.
Claude metadata exposes low effort, adaptive thinking and native structured outputs.
On 2026-10-18 at 12:31:23 UTC, the official Nebius public catalog reported 4096
dimensions and $0.01/million input tokens; the official Claude pricing page listed
$2/million input and $10/million output tokens for Sonnet 5.
[Nebius public catalog](https://tokenfactory.nebius.com/api/public/models_info),
[Claude pricing](https://platform.claude.com/docs/en/about-claude/pricing).

The ignored rate snapshot fingerprint is
`bb35abf7d8410deb441b6dfad11b90e765f97bad1bb6f543ae8c5a593f6fd9c0`.
New paid work still requires fresh verification within 24 hours. Prices and
usage-priced costs are estimates, not final invoices.

Tokenizer revision: `1d8ad4ca9b3dd8059ad90a75d4983776a23d44af` (tokenizers 0.23.3).

| Asset | SHA-256 |
|---|---|
| config.json | `dcccf7c7890c8debc4af8dace8d6acd8dd50bd56d50d4d8b60529381ba3de3d7` |
| tokenizer.json | `83cdf8c3a34f68862319cb1810ee7b1e2c0a44e0864ae930194ddb76bb7feb8d` |
| tokenizer_config.json | `2f58f4bbd7bbce15d683f525954ef3a92cd82f5e06415a9c513859bf8ab72436` |

No weights were downloaded. Queries receive the reviewed instruction once in
client code; documents remain raw. Hosted weight revision/internal preprocessing
are not exposed by model metadata and are not represented as verified immutable behavior.

## Acceptance gates

The unpaid full-corpus preflight produced 22,070 chunks and 8,589,543 embedding
reservation tokens (including overhead). Allowing an eligible retry on every send,
indexing is bounded at $0.17179086 and four questions at $0.18054656, totaling
$0.35233742. This fits both the shared $4 working allowance and the $0.75 Phase 2
cap. The separate $1 reserve remains untouched.

Config fingerprint: `a0af1624cd3e0e7673552e9e1388c26941081acf8436d0aec2718fdeda2808b6`.
Catalog fingerprint: `938573fd948946f45003ce4bb0ddac61ddda4110b52c1b631a03be255c85741c`.

## Actual provider checkpoint

| Measurement | Observed result |
|---|---|
| Expected source-derived chunks | 22,070 |
| Prepared canonical vectors / embedding-cache records | 1,792 / 1,792 |
| Vector dimension | 4,096; validated normalized responses |
| Published complete index / final index fingerprint | None; `index_incomplete` |
| Paid physical attempts | 113 Nebius; 0 Claude inference |
| Billing state | 112 settled; 1 unknown |
| Known provider-reported input tokens | 598,860; timed-out usage unknown |
| Usage-priced ledger accounted amount | $0.006045 |
| Retained unknown reservation | $0.000065 |
| Accounted plus reserved | $0.006110 |
| Remaining shared working / Phase 2 allowance | $3.993890 / $0.743890 |
| Untouched reserve | $1.00 |
| Latest partial build | 69 attempts; 325.812 seconds excluding preflight |
| Timed-out attempt trace latency | 20.485 seconds including local accounting |
| Development campaign / completed receipts | Not run / 0 |
| Query latency / answer or citation-support quality | Unknown; not measured |

The ledger rounds each usage-priced amount up to micro-USD. These amounts are
local accounting estimates, not provider invoice certification. The earlier 44
settled attempts remain fully included in spending/token totals; their individual
latencies are unavailable. The latest partial index trace is
`22c13d319fa943dfb86dc54265d81b15` and stays ignored with the raw artifacts.

The first 704 cached vectors were preserved across a corrected cosine-persistence
check. All matched their original hashes; Chroma drift was at most
`9.498614306192159e-08` L2. No repair model call or ledger reinitialization occurred.
The final timeout then stopped the next batch after 1,792 successful vectors;
its entire reservation remains held, with no assumed zero charge.

## Executed verification

- Keyless: `pytest -m 'not integration' --basetemp=.pytest-tmp/p2-review-full -q`:
  **310 passed, one Windows symlink skip, seven integration deselected**, 72.87s.
- Ruff check/format (130 files), locked dependency check/sync, wheel/sdist build,
  installed CLI help and original/synthetic RAG smokes passed.
- Rebuilt runtime wheel from an empty cwd, no dev packages, sockets blocked:
  help/synthetic smoke passed; evaluation imports zero.
- Native explicit real gate:
  `pytest -m integration tests/test_corpus_integration.py tests/test_rag_integration.py --basetemp=.pytest-tmp/p2-blocked-real -q`:
  **five passed, two failed**, 25.98s. All 55 original PDF/two source-JSONL hashes,
  Phase 1 caches and frozen splits remain unchanged. Complete-index and campaign
  tests fail before dispatch because no complete manifest exists. Two pytest-cache
  permission warnings reflect separate Windows execution identities; no ACL change.
- One independent whole-branch review found four Important issues, corrected with
  RED/GREEN regressions in one pass. See [review evidence](../docs/reviews/phase-2.md).

## Remaining acceptance and recovery

The planned single campaign selects `financebench_id_00222`,
`financebench_id_00464`, and `financebench_id_00476` from distinct companies in
frozen development membership, plus one separate forecast negative. **None has
executed.** Runtime requests contain question text only, without gold filters.
Raw questions, answers, passages and traces remain ignored. Holdout is untouched.

The reviewed design says an uncertain timeout retains its full reservation and
does not trigger an automatic retry. Paid execution is stopped pending explicit
resumption review. A permitted resume would reuse all 1,792 validated cached
vectors and retain the $0.000065 unknown amount; only missing batches could be
sent. The uncertain batch may be billed again, so this is an explicit new paid
invocation rather than a zero-cost replay. All original dollar/time/model limits
would remain in force, with another stop on an uncertain failure.

The fresh unpaid recovery preflight passed with the same source/config/catalog/
rate fingerprints: **20,254 uncached chunks**, 7,866,651 reservation input tokens,
$0.15733302 estimated indexing allowance plus $0.18054656 for four questions,
total **$0.33787958**. This fits the $0.743890 remaining Phase 2 allowance while
the old unknown reservation stays held. Cache reuse can cover 24 additional
remaining windows sharing already cached submitted text. Provider network calls
in this preflight: **zero**. The ignored `phase2-resume-preflight.json` preserves
the full report. This is a recovery estimate, not resumption approval or spending.

After a complete source-validated index, execute the opted-in harness once, inspect
each answer's original PDF/page/quote, company, year, units and calculation, then
record actual semantic failures and costs. No full-corpus or quality claim is
inferred from this partial embedding build. Phase 3, publication and integration
of this branch remain unstarted.
