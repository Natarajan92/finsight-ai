"""Development-only joins and retrieval proxies; never imported by runtime."""

import json
from pathlib import Path

from finsight.contracts import QueryRequest
from finsight.contracts.base import fingerprint
from finsight.ingestion.cache import write_json_atomic
from finsight.ingestion.fingerprints import sha256_file
from finsight.runtime.errors import FinsightError

from .benchmark import load_benchmark
from .splits import SplitManifest, SplitPolicy, freeze_splits, validate_split_pair


def _pages(candidates):
    return {(c.chunk.document_id, s.page_index) for c in candidates for s in c.chunk.source_spans}


def retrieval_metrics(ranked, gold_pages, *, pool=None):
    if not gold_pages:
        raise ValueError("Gold pages must be nonempty")
    selected = _pages(ranked[:5])
    first = next((i for i, c in enumerate(ranked[:15], 1) if _pages((c,)) & gold_pages), None)
    return dict(
        page_hit_at_5=float(bool(selected & gold_pages)),
        gold_page_recall_at_5=len(selected & gold_pages) / len(gold_pages),
        mrr_at_15=1 / first if first else 0.0,
        candidate_pool_coverage=len(_pages(ranked if pool is None else pool) & gold_pages)
        / len(gold_pages),
    )


def development_cases(questions: Path, corpus, split_dir: Path):
    cases = load_benchmark(questions, corpus)
    dev = SplitManifest.model_validate_json((split_dir / "development.json").read_text())
    hold = SplitManifest.model_validate_json((split_dir / "holdout.json").read_text())
    policy = SplitPolicy.model_validate_json((split_dir / "split-policy.json").read_text())
    validate_split_pair(dev, hold)
    if freeze_splits(cases, policy, sha256_file(questions), corpus.source_fingerprint) != (
        dev,
        hold,
    ):
        raise FinsightError("experiment_split_integrity")
    return tuple(c for c in cases if c.financebench_id in dev.question_ids), dev


def run_development_comparison(lab, questions: Path, split_dir: Path, *, allow_paid=False):
    # The legacy baseline campaign's own replay validator establishes this gate.
    from .smoke import run_development_campaign

    try:
        run_development_campaign(lab.settings, lab.baseline, questions, split_dir, allow_paid=False)
    except FinsightError:
        raise FinsightError("baseline_acceptance_pending") from None
    cases, split = development_cases(questions, lab.corpus, split_dir)
    if len(cases) != 36 or len(lab.corpus.documents) != 53:
        raise FinsightError("experiment_scope")
    identity = dict(
        source=lab.corpus.source_fingerprint,
        split=split.split_fingerprint,
        dataset=sha256_file(questions),
        configs=[lab.config(a).fingerprint() for a in "ABCD"],
    )
    path = lab.trace_root / ("comparison-" + fingerprint(identity) + ".json")
    if path.exists():
        receipt = json.loads(path.read_text())
        if receipt.get("identity") != identity or not receipt.get("complete"):
            raise FinsightError("experiment_interrupted")
        # Revalidate pools and rerank artifacts against the live source/index before replaying.
        for case, row in zip(cases, receipt["records"], strict=True):
            traces = lab.run_arms(QueryRequest(question=case.question), allow_paid=False)
            if (
                any(t.status != "complete" for t in traces)
                or row["question_id"] != case.financebench_id
            ):
                raise FinsightError("experiment_replay_integrity")
            if row["selection_fingerprints"] != [
                fingerprint([c.model_dump(mode="json") for c in t.selected]) for t in traces
            ]:
                raise FinsightError("experiment_replay_integrity")
        return {**receipt, "replay": True}
    if lab.preflight("comparison", query_count=36)["status"] != "ready":
        raise FinsightError("budget_exceeded")
    receipt = dict(
        identity=identity,
        complete=False,
        records=[],
        scope="frozen-development",
        generation_calls=0,
    )
    write_json_atomic(path, receipt)
    documents = {d.doc_name: d.document_id for d in lab.corpus.documents}
    for case in cases:
        traces = lab.run_arms(QueryRequest(question=case.question), allow_paid=allow_paid)
        gold = {(documents[e.doc_name], e.evidence_page_num) for e in case.evidence}
        metrics = {
            t.arm: retrieval_metrics(
                t.rerank_result.candidates if t.rerank_result else t.pool, gold, pool=t.pool
            )
            if t.status == "complete"
            else None
            for t in traces
        }
        receipt["records"].append(
            dict(
                question_id=case.financebench_id,
                metrics=metrics,
                trace_ids=[t.run_id for t in traces],
                selection_fingerprints=[
                    fingerprint([c.model_dump(mode="json") for c in t.selected]) for t in traces
                ],
            )
        )
        write_json_atomic(path, receipt)
        if any(t.status != "complete" for t in traces):
            raise FinsightError("experiment_comparison_incomplete")
    receipt["complete"] = True
    receipt["aggregate_metrics"] = {
        arm: {
            name: sum(r["metrics"][arm][name] for r in receipt["records"]) / len(cases)
            for name in receipt["records"][0]["metrics"][arm]
        }
        for arm in "ABCD"
    }
    write_json_atomic(path, receipt)
    return {**receipt, "replay": False}
