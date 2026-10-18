import json

import pytest

from finsight.contracts.base import fingerprint
from finsight.contracts.ingestion import ExtractionConfig
from finsight.evaluation.audit import audit_benchmark
from finsight.evaluation.benchmark import load_benchmark
from finsight.evaluation.cli import main
from finsight.evaluation.splits import SplitManifest, SplitPolicy, freeze_splits
from finsight.ingestion.cache import extract_cached, write_json_atomic
from finsight.ingestion.fingerprints import sha256_file


def _swapped_pair(cases, dev, hold):
    by_id = {c.financebench_id: c for c in cases}
    original_dev, original_hold = next(
        (a, b)
        for a in dev.question_ids
        for b in hold.question_ids
        if (by_id[a].company, by_id[a].question_reasoning)
        == (by_id[b].company, by_id[b].question_reasoning)
    )
    dev_ids = sorted((set(dev.question_ids) - {original_dev}) | {original_hold})
    hold_ids = sorted((set(hold.question_ids) - {original_hold}) | {original_dev})
    fields = (
        "seed",
        "algorithm_version",
        "dataset_sha256",
        "source_fingerprint",
        "policy_fingerprint",
    )
    metadata = {key: getattr(dev, key) for key in fields}
    digest = fingerprint({**metadata, "development": dev_ids, "holdout": hold_ids})
    return (
        SplitManifest.model_validate(
            {**dev.model_dump(), "question_ids": dev_ids, "split_fingerprint": digest}
        ),
        SplitManifest.model_validate(
            {**hold.model_dump(), "question_ids": hold_ids, "split_fingerprint": digest}
        ),
    )


def test_development_audit_never_examines_holdout_annotations(benchmark_fixture, tmp_path):
    path, corpus, _ = benchmark_fixture
    cases = load_benchmark(path, corpus)
    dev, hold = freeze_splits(
        cases, SplitPolicy(dataset_sha256="a" * 64), "a" * 64, corpus.source_fingerprint
    )
    cache_root = tmp_path / "cache"
    for document in corpus.documents:
        extract_cached(path.parent / "pdfs", document, ExtractionConfig(), cache_root)
    changed = tuple(
        c.model_copy(update={"evidence": ()}) if c.financebench_id in hold.question_ids else c
        for c in cases
    )
    summary, details = audit_benchmark(changed, corpus, dev, hold, cache_root)
    assert summary["selected_questions"] == 52 and summary["development_evidence_references"] == 36
    assert summary["development_normalized_exact_matches"] == 36
    assert {row["question_id"] for row in details} == set(dev.question_ids)
    assert "GOLD_ONLY" not in json.dumps(summary)


def test_checksum_consistent_but_wrong_membership_is_rejected(benchmark_fixture, tmp_path):
    path, corpus, _ = benchmark_fixture
    cases = load_benchmark(path, corpus)
    dev, hold = freeze_splits(
        cases, SplitPolicy(dataset_sha256="a" * 64), "a" * 64, corpus.source_fingerprint
    )
    for document in corpus.documents:
        extract_cached(path.parent / "pdfs", document, ExtractionConfig(), tmp_path / "cache")
    dev, hold = _swapped_pair(cases, dev, hold)
    with pytest.raises(ValueError):
        audit_benchmark(cases, corpus, dev, hold, tmp_path / "cache")


def test_cli_freeze_and_validate_synthetic_data(benchmark_fixture, tmp_path, monkeypatch, capsys):
    path, corpus, _ = benchmark_fixture
    monkeypatch.chdir(tmp_path)
    manifest = tmp_path / "manifest.json"
    policy = tmp_path / "policy.json"
    write_json_atomic(manifest, corpus.model_dump(mode="json"))
    write_json_atomic(policy, SplitPolicy(dataset_sha256=sha256_file(path)).model_dump(mode="json"))
    split_dir = tmp_path / "splits"
    assert (
        main(
            [
                "split",
                "--questions",
                str(path),
                "--manifest",
                str(manifest),
                "--policy",
                str(policy),
                "--output-dir",
                str(split_dir),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["holdout"] == 16
    cache_root = tmp_path / "cache"
    for document in corpus.documents:
        extract_cached(tmp_path / "pdfs", document, ExtractionConfig(), cache_root)
    assert (
        main(
            [
                "validate",
                "--questions",
                str(path),
                "--manifest",
                str(manifest),
                "--split-dir",
                str(split_dir),
                "--split",
                "development",
                "--cache-root",
                str(cache_root),
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert "GOLD_ONLY" not in output and "GOLD_PAGE_ONLY" not in output
    assert (tmp_path / "data/evaluation/development-extraction.json").exists()
    diagnostics = tmp_path / "data/evaluation/development-extraction.json"
    before = diagnostics.read_bytes()
    dev, hold = freeze_splits(
        load_benchmark(path, corpus),
        SplitPolicy(dataset_sha256=sha256_file(path)),
        sha256_file(path),
        corpus.source_fingerprint,
    )
    dev, hold = _swapped_pair(load_benchmark(path, corpus), dev, hold)
    write_json_atomic(split_dir / "development.json", dev.model_dump(mode="json"))
    write_json_atomic(split_dir / "holdout.json", hold.model_dump(mode="json"))
    assert (
        main(
            [
                "validate",
                "--questions",
                str(path),
                "--manifest",
                str(manifest),
                "--split-dir",
                str(split_dir),
                "--split",
                "development",
                "--cache-root",
                str(cache_root),
            ]
        )
        == 1
    )
    assert diagnostics.read_bytes() == before


def test_cli_refuses_holdout_feedback():
    with pytest.raises(SystemExit) as exc:
        main(
            [
                "validate",
                "--questions",
                "q",
                "--manifest",
                "m",
                "--split-dir",
                "s",
                "--cache-root",
                "c",
                "--split",
                "holdout",
            ]
        )
    assert exc.value.code == 2
