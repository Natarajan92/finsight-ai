# AMD application engineering journal

## AMD-001 — Finish the financial-document RAG slice

**Date:** 2026-10-19 IST; exact user-message times unavailable.
**Checkout:** `feat/phase-3-retrieval-experiments`, initial HEAD `4759192`.

**Human prompts, verbatim:**

> Lets finish our application development for one Company AMD

> use your judgement with existing document. Goal is to develop a RAG on financial documents

**Decision:** Use the existing AMD_2022_10K source and complete 313-chunk index to
deliver a functional single-filing Streamlit app. The human authorized scope
judgment and execution. This extends the earlier Phase 3 restriction on UI for
this AMD slice; it does not expand the corpus or authorize publication. Preserve
the existing dirty experiment work and executed notebook. Implement natively in
the retained checkout; obtain one independent final review.

**Architecture:** Streamlit -> AMD workspace -> durable scoped pilot -> existing
`ApplicationService.answer(QueryRequest)`. Questions carry explicit AMD/document/
filing scope. Source browsing is offline. New purchases require the live switch;
immutable receipts bind request/source/index/config and validated citations.
Interrupted receipts block repurchase. Reruns revalidate receipts without live
calls. Model/source text is displayed literally, keeping dollar signs and
untrusted Markdown intact. No evaluator annotations enter runtime.

**Observed failures and fixes:**

- Initial suite: 335 passed, one missing `experiment_pilot` import failure,
  one unavailable Windows symlink skip, seven integration deselections. Completed
  the missing AMD answer path with explicit scope and replay tests.
- Ten new cases first failed at missing implementations, then passed. Streamlit
  AppTest's Windows asyncio loop needed a private loopback socketpair: a narrow
  helper permits only that stdlib construction while app sockets remain blocked.
- Real startup found the existing tokenizer unreadable by the sandbox identity.
  An approved elevated read verified the unchanged artifact. No ACLs were altered.
- Real trace serialization exposed an integer default for a Decimal money field.
  A warnings-as-error regression failed, then passed with `Decimal("0")`.
- Independent review found currency rendered as math and session state bypassing
  replay checks. Both were reproduced RED, fixed, and verified GREEN. Literal
  output also avoids model-authored Markdown images/links.
- Full-checkout notebook tests reject the human's executed notebook. Preserved
  it byte-for-byte and verified the committed notebook in an isolated snapshot.
- First snapshot scratch paths exceeded Windows file limits. Shortening the test
  scratch root fixed the file-renaming errors; no runtime checks were relaxed.

**Verification:** final clean snapshot **357 passed, one skip, seven integration
deselections**; Ruff lint/format passed for 156 files. Focused app/factory/contracts
suite: 72 passed. Locked dependencies, wheel/sdist, secret/artifact inspection and
both synthetic smokes passed. Real AMD query answered with a verified page-54
citation, one generation, one query embedding, $0.01191832 usage-priced cost and
9,282 ms latency. A new workspace and actual Streamlit AppTest replayed it with
paid-client construction forbidden. Source-page browsing passed. HTTP health is
200; browser screenshots were unavailable because no browser surface is connected.

**Budget:** accounted $0.030903, existing uncertain reservation $0.000065,
working availability $3.969032; the $1 reserve is untouched. No resets, increased
limits or automatic timeout retries. Raw traces and receipts remain ignored.

**Scope limits:** AMD 2022 Form 10-K only. Full-corpus baseline acceptance,
semantic/reranker comparison, comprehensive answer evaluation and publication
remain separate. One successful answer establishes neither 95% faithfulness nor
the latency target. The notebook hash is unchanged and all changes remain local.

**Evidence:** [verification record](../../results/amd-application-smoke.md),
[design](../superpowers/specs/2026-10-19-amd-application-design.md),
[plan](../superpowers/plans/2026-10-19-amd-application.md).

## AMD-002 — Publish code and prepare the next phase branch

**Date:** 2026-10-19 IST; exact user-message time unavailable.

**Human prompt, verbatim:**

> push the code github and create new branch for next phase implementation.

This authorizes publication of the AMD code to the verified existing remote
`Natarajan92/finsight-ai`, overriding the earlier local-only delivery constraint.
Publish the existing `feat/phase-3-retrieval-experiments` branch and open its review
PR against `main`. Then create and publish `feat/phase-4-evaluation` from that
published tip and switch the checkout to it. The next branch is intentionally
based on the current implementation; no merge or next-phase code is requested.

The AMD app depends on the existing shared-service and experiment-facade changes,
so include those source files and their tests in the same reviewable publication.
Exclude the human's executed notebook and unrelated Phase 2 plan edits. Preserve
their working bytes, all original PDFs, caches, private traces and budget storage.
Verify the exact staged tree with keyless tests, lint, formatting, smokes and a
credential scan before committing/pushing. Authentication and repository identity
were verified using the existing GitHub CLI credentials; no credentials changed.
