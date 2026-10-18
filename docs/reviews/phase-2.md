# Phase 2 local review checkpoint

Status: implementation and the independent review fix pass are verified;
real-source/provider acceptance is **blocked by an uncertain Nebius timeout**.
Phase 2 is incomplete.

## Scope and evidence

Branch `feat/phase-2-baseline-rag`, based on merged Phase 1
`6db76b2c887e86aca6fa58ab08706443b0bd637b`. No push, PR publication or merge.

- Native execution with TDD and per-task commits; see the
  [Phase 2 journal](../engineering-journal/phase-02.md).
- Most recent keyless gate: 310 passed, one Windows symlink skip, seven integration
  tests deselected. Ruff lint/format passed. Runtime wheel help/synthetic RAG passed
  from an empty cwd with sockets blocked and no evaluation imports.
- Explicit local-source gate: five passed. All 55 selected original PDFs, both
  source JSONL hashes, frozen splits and Phase 1 caches remain unchanged.
- Public tokenizer assets prepared and hash-verified; provider model metadata
  confirms the configured IDs and Claude structured outputs/adaptive/low effort.
- Persistent budget initialized once. Full-corpus preflight fits: 22,070 chunks,
  $0.35233742 conservative indexing/four-query allowance, below the $0.75 phase cap.
  The build stopped after 1,792 vectors: $0.006045 accounted and $0.000065 held
  unknown. No Claude inference or development answer campaign has run.

## Independent review

One fresh-context reviewer inspected `6db76b2..eecba8f` read-only and ran 160
focused keyless tests plus temporary synthetic probes. It found no Critical and
four Important issues: elapsed provider waits, replay provenance/prompt binding,
duplicate budget initialization and persisted cosine-vector hashes. Each was
reproduced with failing regressions and corrected in one pass, commit `593ca53`.
The full keyless suite then passed: 310 tests in 72.87 seconds. The rebuilt isolated
runtime wheel also passed with sockets blocked, no dev packages and no evaluation
imports. A second review was not dispatched under the native execution workflow.

Deferred Minor: a standalone `will` in a historical commitment question can trigger
conservative forecast abstention. Semantic support/year-column association remain
separate manual checks; later phases, OCR and exact ANN search are outside this gate.

## Remaining gates

The real gate explicitly returned five passes and two failures in 25.98 seconds:
complete-index/campaign fail closed on the missing completion manifest before any
new dispatch. Original sources, Phase 1 caches and split membership remain intact.
The current unknown reservation cannot be released by assuming the timeout was free.

Review an explicit resumption while preserving cached vectors and unknown money;
the approved design prohibits automatic uncertain retries. Then finish the full
index and the one development campaign, inspect source mappings and semantic
claim/unit/year/calculation correctness, and record actual failures without buying
extra answers to obtain a success. Preserve the completed review regressions.
The fresh unpaid recovery estimate is $0.33787958 for remaining indexing and four
questions, below the $0.743890 phase headroom; the uncertain amount remains held.

Citation containment and three development samples cannot establish the 95%
faithfulness or eight-second latency targets. OCR, semantic chunking, reranking,
holdout generation, UI and deployment remain later phases. Remote CI is unknown
until separate publication approval.

## Rulings made during native execution

These preserve the execution ledger's order and costs for human review. None is
described as an additional human approval.

| # | Decision | Cost or limitation if wrong |
|---|---|---|
| 1 | Use the selected feature checkout | No separate linked-worktree isolation |
| 2 | Adapt bash bookkeeping to Python/PowerShell | Manual helper-parity verification |
| 3 | Inject tokenizer/pages/embeddings explicitly | More explicit caller dependencies |
| 4 | Regenerate source windows on reopen; paginate vector checks | Additional local startup latency; original exact-hash assumption corrected in #10 |
| 5 | Use homogeneous typed two-operand arrays for SDK conversion | Malformed output is rejected without repair |
| 6 | Pass the actual request to authorize period comparisons | Callers must supply it; otherwise cross-period math refuses |
| 7 | Separate a one-hour bulk job from 45-second answers | Longer bulk execution; superseded by #8 |
| 8 | Extend only the bulk bound to four hours | A bulk command may occupy four hours |
| 9 | Overlap the single read-only review with live acceptance | Fingerprint-changing fixes could invalidate staged work |
| 10 | Hash canonical float32 references; allow `1e-6` stored L2 drift | About 345 MiB extra artifacts and deliberately accepted tiny numeric drift |
| 11 | Keep semantic support/year-column association a manual gate | Three samples cannot establish broad faithfulness |
| 12 | Retain exact two-operand arithmetic | Useful rounded or complex calculations may refuse |
| 13 | Keep OCR/table completeness deferred with warnings | Relevant facts may be unavailable or ambiguous |
| 14 | Retain selected headings and flag missing headings | Unit/year context may remain missing |
| 15 | Persist observed ANN pools; stabilize returned ties | Later ANN runs may select another tied pool |
| 16 | Keep conservative manifest-name clarification | Common company aliases may refuse |
| 17 | Check local consistency without cryptographic tamper-proof storage | An administrator can replace every authority |
| 18 | Record overruns; exclude unrelated account activity from guarantees | Invoices may exceed estimates or include other use |
| 19 | Bind the index to the complete runtime configuration | Extra local rebuild/revalidation; embeddings remain reusable |
| 20 | Keep public errors nonretryable | Limited retry guidance for callers |
| 21 | Require actual campaign/manual inspection for phase completion | A provider/latency failure blocks acceptance |
| 22 | Verify final prose/repairs locally after the review checkpoint | Final prose and repairs have no second reviewer |
| 23 | Keep experiments/scoring/UI/publication in later phases | No four-arm comparison or UI yet |
| 24 | Bound synchronous waits with at most 16 daemon calls | Remote work can continue; full unknown reservation remains; capacity can block |
| 25 | Bind budget identity to an independent durable authority | Moving/lost authorities require reconciliation |
| 26 | Stop after the uncertain timeout and prepare a recovery review | Acceptance waits despite monetary headroom |
| 27 | Commit a truthful blocked checkpoint, leaving Task 10 incomplete | One extra interim documentation commit |

Deferred minors: blanket standalone `will` can refuse historical commitment
questions. No other Minor findings were deferred.
