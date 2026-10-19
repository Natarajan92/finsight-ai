"""Real PDF/index/service evaluation, with only provider boundaries replaced."""

import importlib.util
import json
from decimal import Decimal

import pytest
from test_amd_app import amd_lab as amd_lab_fixture  # noqa: F401 -- pytest fixture registration

from finsight.contracts.base import fingerprint
from finsight.contracts.ingestion import CorpusManifest
from finsight.evaluation.benchmark import load_benchmark
from finsight.evaluation.splits import SplitPolicy, freeze_splits, write_splits
from finsight.ingestion.cache import write_json_atomic
from finsight.ingestion.fingerprints import sha256_file
from finsight.runtime.errors import FinsightError


@pytest.fixture
def evaluation_inputs(request, benchmark_fixture, tmp_path, monkeypatch):
    from finsight.runtime.experiment_factory import ExperimentLab

    lab, generator, calls, service = request.getfixturevalue("amd_lab_fixture")
    questions, original, rows = benchmark_fixture
    document = lab.corpus.documents[0]
    documents = tuple(d for d in original.documents if d.company != "AMD") + (document,)
    parent = CorpusManifest(
        documents=documents,
        metadata_sha256=original.metadata_sha256,
        source_fingerprint=fingerprint(sorted([[d.doc_name, d.sha256] for d in documents])),
    )
    for row in rows:
        if row["company"] == "AMD":
            row["doc_name"] = document.doc_name
            row["question"] = f"What was revenue in 2022? {row['financebench_id']}"
            row["answer"] = "100 USD millions"
            row["justification"] = "PRIVATE_EVALUATOR_RATIONALE"
            for evidence in row["evidence"]:
                evidence["doc_name"] = document.doc_name
    questions.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    policy = SplitPolicy(dataset_sha256=sha256_file(questions))
    cases = load_benchmark(questions, parent)
    dev, hold = freeze_splits(cases, policy, sha256_file(questions), parent.source_fingerprint)
    split = tmp_path / "splits"
    write_splits(split, dev, hold)
    write_json_atomic(split / "split-policy.json", policy.model_dump(mode="json"))
    manifest = tmp_path / "parent.json"
    manifest.write_text(parent.model_dump_json(), encoding="utf-8")
    lab.settings.manifest_path = manifest
    rates = lab.dispatcher.rates.model_copy(
        update={
            "cards": tuple(
                c.model_copy(update={"input_per_million": Decimal("0.01")})
                if c.provider == "nebius"
                else c
                for c in lab.dispatcher.rates.cards
            )
        }
    )
    lab.dispatcher.rates = rates
    lab.settings.rates_path.write_text(rates.model_dump_json(), encoding="utf-8")
    lab._generator, lab._counter = generator, service.counter
    monkeypatch.setattr(lab, "application", ExperimentLab.application.__get__(lab))
    return lab, generator, calls, service, questions, split, tmp_path / "evaluation", dev, hold


def campaign():
    assert importlib.util.find_spec("finsight.evaluation.campaign"), "Missing evaluation campaign"
    from finsight.evaluation import campaign

    return campaign


def test_plan_selects_all_five_amd_dev_cases_without_dispatch(evaluation_inputs):
    lab, generator, calls, _, questions, split, output, dev, hold = evaluation_inputs
    count = len(calls)
    plan = campaign().plan_evaluation(lab, questions, split)
    assert plan["status"] == "ready" and len(plan["question_ids"]) == 5
    assert set(plan["question_ids"]) <= set(dev.question_ids)
    assert not set(plan["question_ids"]) & set(hold.question_ids)
    assert Decimal(plan["maximum_usd"]) <= Decimal("0.25")
    with pytest.raises(FinsightError, match="paid_not_authorized"):
        campaign().run_evaluation(lab, questions, split, output)
    assert not output.exists() and generator.calls == 0 and len(calls) == count


def test_live_campaign_scores_then_replays_with_no_new_calls_or_gold_leakage(evaluation_inputs):
    lab, generator, calls, service, questions, split, output, _, _ = evaluation_inputs
    module = campaign()
    run = module.run_evaluation(lab, questions, split, output, allow_paid=True)
    assert run.complete and len(run.records) == 5 and generator.calls == 5
    assert run.runtime_configs["A"]["baseline"]["generation_model"] == "claude-sonnet-5"
    assert run.runtime_config_fingerprints["A"] == lab.config("A").fingerprint()
    assert run.index_fingerprints["A"] == lab.open("A").manifest.fingerprint()
    assert all(r.match["match"] is True for r in run.records)
    assert all(r.metrics["page_hit_at_5"] == 1 for r in run.records)
    from finsight.observability.tracing import JsonlTraceRecorder

    trace = JsonlTraceRecorder(lab.trace_root / "answers").load(run.records[-1].trace_id)
    assert "PRIVATE_EVALUATOR_RATIONALE" not in trace.prompt.user
    assert "100 USD millions" not in trace.request.question
    count = len(calls)
    again = module.run_evaluation(lab, questions, split, output)
    assert again.replay and generator.calls == 5 and len(calls) == count
    assert again.new_cost_usd == Decimal(0) and again.new_reservation_usd == Decimal(0)
    assert [r.trace_fingerprint for r in again.records] == [
        r.trace_fingerprint for r in run.records
    ]


def test_unavailable_arms_and_budget_conflict_stop_before_generation(evaluation_inputs):
    lab, generator, calls, _, questions, split, output, _, _ = evaluation_inputs
    module = campaign()
    count = len(calls)
    assert module.plan_evaluation(lab, questions, split, arms="AB")["status"] == "assets_missing"
    with pytest.raises(FinsightError, match="evaluation_assets_missing"):
        module.run_evaluation(lab, questions, split, output, arms="AB", allow_paid=True)
    plan = module.plan_evaluation(lab, questions, split, max_cost_usd=Decimal("0.000001"))
    assert plan["status"] == "budget_conflict"
    with pytest.raises(FinsightError, match="budget_exceeded"):
        module.run_evaluation(
            lab, questions, split, output, max_cost_usd=Decimal("0.000001"), allow_paid=True
        )
    assert generator.calls == 0 and len(calls) == count


def test_changed_frozen_dataset_fails_before_purchase(evaluation_inputs):
    lab, generator, calls, _, questions, split, output, _, _ = evaluation_inputs
    questions.write_text(questions.read_text() + "\n")
    count = len(calls)
    with pytest.raises((ValueError, FinsightError)):
        campaign().run_evaluation(lab, questions, split, output, allow_paid=True)
    assert generator.calls == 0 and len(calls) == count


def test_terminal_error_is_visible_and_cannot_be_repurchased(evaluation_inputs):
    lab, generator, calls, _, questions, split, output, _, _ = evaluation_inputs
    generator.failure = True
    first = campaign().run_evaluation(lab, questions, split, output, allow_paid=True)
    assert not first.complete and len(first.records) == 1 and first.records[0].status == "error"
    count = len(calls)
    second = campaign().run_evaluation(lab, questions, split, output, allow_paid=True)
    assert not second.complete and generator.calls == 1 and len(calls) == count


def test_tampered_runtime_trace_blocks_replay_before_other_dispatch(evaluation_inputs):
    lab, generator, calls, _, questions, split, output, _, _ = evaluation_inputs
    first = campaign().run_evaluation(lab, questions, split, output, allow_paid=True)
    trace = lab.trace_root / "answers" / (first.records[0].trace_id + ".jsonl")
    payload = json.loads(trace.read_text())
    payload["request"]["question"] = "Forged runtime question"
    trace.write_text(json.dumps(payload))
    count = len(calls)
    with pytest.raises(FinsightError, match="integrity"):
        campaign().run_evaluation(lab, questions, split, output, allow_paid=True)
    assert generator.calls == 5 and len(calls) == count


def test_fixed_and_reranked_arms_share_candidate_pools_and_one_query_vector(evaluation_inputs):
    from types import SimpleNamespace

    from test_reranking import tiny_tokenizer

    from finsight.retrieval.reranking import LocalReranker

    lab, generator, calls, _, questions, split, output, _, _ = evaluation_inputs
    lab._reranker = LocalReranker(
        SimpleNamespace(
            tokenizer=tiny_tokenizer(),
            fingerprint=lambda: "b" * 64,
            score=lambda encodings, context: [0.0] * len(encodings),
        ),
        lab.config("C").reranker,
        output.parent / "rerank-cache",
    )
    count = len(calls)
    run = campaign().run_evaluation(lab, questions, split, output, arms="AC", allow_paid=True)
    assert run.complete and len(run.records) == 10 and generator.calls == 10
    assert len(calls) == count + 5
    for identity in run.question_ids:
        records = [r for r in run.records if r.question_id == identity]
        assert len({r.dense_pool_fingerprint for r in records}) == 1
    again = campaign().run_evaluation(lab, questions, split, output, arms="AC")
    assert again.replay and generator.calls == 10 and len(calls) == count + 5


def test_run_receipt_is_reopened_after_acquiring_its_lock(evaluation_inputs, monkeypatch):
    from contextlib import contextmanager

    lab, generator, calls, _, questions, split, output, _, _ = evaluation_inputs
    module = campaign()
    module.run_evaluation(lab, questions, split, output, allow_paid=True)
    path = next(output.rglob("run.json"))
    original_lock = module.index_build_lock

    @contextmanager
    def corrupt_under_lock(root):
        with original_lock(root):
            path.write_text("{}")
            yield

    monkeypatch.setattr(module, "index_build_lock", corrupt_under_lock)
    count = len(calls)
    with pytest.raises(FinsightError, match="evaluation_run_integrity"):
        module.run_evaluation(lab, questions, split, output, allow_paid=True)
    assert generator.calls == 5 and len(calls) == count


def test_admission_error_does_not_fabricate_zero_retrieval_metrics(evaluation_inputs, monkeypatch):
    lab, generator, _, _, questions, split, output, _, _ = evaluation_inputs

    def failed_counter(*args):
        raise FinsightError("token_count_unavailable")

    monkeypatch.setattr(lab._counter, "count_text", failed_counter)
    run = campaign().run_evaluation(lab, questions, split, output, allow_paid=True)
    assert not run.complete and generator.calls == 0
    assert run.records[0].metrics["page_hit_at_5"] is None
    assert run.records[0].match["match"] is None
