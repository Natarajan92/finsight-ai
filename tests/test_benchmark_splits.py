from collections import Counter

import pytest

from finsight.evaluation.benchmark import load_benchmark
from finsight.evaluation.splits import (
    SplitManifest,
    SplitPolicy,
    freeze_splits,
    validate_split_pair,
    write_splits,
)


def construct(benchmark_fixture):
    path, corpus, _ = benchmark_fixture
    cases = load_benchmark(path, corpus)
    policy = SplitPolicy(dataset_sha256="a" * 64)
    dev, hold = freeze_splits(cases, policy, "a" * 64, corpus.source_fingerprint)
    return cases, policy, dev, hold


def test_exact_company_reasoning_distribution_and_fingerprints(benchmark_fixture):
    cases, _, dev, hold = construct(benchmark_fixture)
    assert len(dev.question_ids) == 36 and len(hold.question_ids) == 16
    assert not set(dev.question_ids) & set(hold.question_ids)
    assert set(dev.question_ids) | set(hold.question_ids) == {c.financebench_id for c in cases}
    mapping = {c.financebench_id: c for c in cases}
    hold_counts = Counter(mapping[i].company for i in hold.question_ids)
    assert dict(hold_counts) == {
        "AMD": 3,
        "American Express": 2,
        "PepsiCo": 3,
        "Boeing": 2,
        "Amcor": 3,
        "Johnson & Johnson": 3,
    }
    totals = Counter(c.question_reasoning for c in cases)
    for ids in (dev.question_ids, hold.question_ids):
        represented = {mapping[i].question_reasoning for i in ids}
        assert all(label in represented for label, count in totals.items() if count >= 2)
    repeated = Counter((c.company, c.question_reasoning) for c in cases)
    dev_strata = {(mapping[i].company, mapping[i].question_reasoning) for i in dev.question_ids}
    hold_strata = {(mapping[i].company, mapping[i].question_reasoning) for i in hold.question_ids}
    assert sum(key in dev_strata & hold_strata for key, n in repeated.items() if n >= 2) == 12
    assert dev.split_fingerprint == hold.split_fingerprint
    assert SplitManifest.model_validate_json(dev.model_dump_json()) == dev
    validate_split_pair(dev, hold)


def test_order_and_gold_independence(benchmark_fixture):
    cases, policy, dev, hold = construct(benchmark_fixture)
    changed = tuple(
        c.model_copy(
            update={
                "answer": "REPLACED_GOLD",
                "justification": "changed",
                "question": "Different synthetic wording",
                "evidence": (),
            }
        )
        for c in reversed(cases)
    )
    assert freeze_splits(changed, policy, "a" * 64, dev.source_fingerprint) == (dev, hold)


def test_refuses_wrong_dataset_or_counts(benchmark_fixture):
    cases, policy, dev, _ = construct(benchmark_fixture)
    for items, sha in [(cases, "b" * 64), (cases[:-1], "a" * 64)]:
        with pytest.raises(ValueError):
            freeze_splits(items, policy, sha, dev.source_fingerprint)


def test_frozen_pair_is_idempotent_and_cannot_be_replaced(benchmark_fixture, tmp_path):
    _, _, dev, hold = construct(benchmark_fixture)
    write_splits(tmp_path, dev, hold)
    write_splits(tmp_path, dev, hold)
    before = (tmp_path / "development.json").read_bytes()
    forged = hold.model_copy(update={"split_fingerprint": "b" * 64})
    with pytest.raises(ValueError):
        write_splits(tmp_path, dev, forged)
    assert (tmp_path / "development.json").read_bytes() == before


def test_manifest_membership_is_only_ids_and_metadata(benchmark_fixture):
    _, _, dev, _ = construct(benchmark_fixture)
    payload = dev.model_dump_json()
    assert "GOLD_ONLY" not in payload and 'question"' not in payload
    assert all(
        key not in dev.model_dump() for key in ("answer", "evidence", "justification", "company")
    )
    with pytest.raises(ValueError):
        SplitManifest.model_validate({**dev.model_dump(), "answer": "injected"})
