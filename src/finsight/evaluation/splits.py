"""Deterministic, question-level split construction; no RAG execution."""

import json
from collections import Counter, defaultdict
from fractions import Fraction
from itertools import product
from pathlib import Path
from typing import Literal, Self

from pydantic import model_validator

from finsight.contracts.base import Contract, NonBlank, Sha256, fingerprint
from finsight.ingestion.cache import write_json_atomic
from finsight.ingestion.manifest import COMPANIES, company_key

from .benchmark import BenchmarkCase


class SplitPolicy(Contract):
    schema_version: Literal["1"] = "1"
    algorithm_version: Literal["company-reasoning-v1"] = "company-reasoning-v1"
    seed: Literal[42] = 42
    development_count: Literal[36] = 36
    holdout_count: Literal[16] = 16
    dataset_sha256: Sha256

    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


class SplitManifest(Contract):
    schema_version: Literal["1"] = "1"
    split: Literal["development", "holdout"]
    question_ids: tuple[NonBlank, ...]
    seed: Literal[42] = 42
    algorithm_version: Literal["company-reasoning-v1"] = "company-reasoning-v1"
    dataset_sha256: Sha256
    source_fingerprint: Sha256
    policy_fingerprint: Sha256
    selected_ids_fingerprint: Sha256
    split_fingerprint: Sha256

    @model_validator(mode="after")
    def valid_membership(self) -> Self:
        expected = 36 if self.split == "development" else 16
        if (
            len(self.question_ids) != expected
            or tuple(sorted(set(self.question_ids))) != self.question_ids
        ):
            raise ValueError("Split requires sorted, unique IDs and its exact approved count")
        return self


def _split_hash(metadata: dict, development: tuple[str, ...], holdout: tuple[str, ...]) -> str:
    return fingerprint({**metadata, "development": list(development), "holdout": list(holdout)})


def validate_split_pair(development: SplitManifest, holdout: SplitManifest) -> None:
    if development.split != "development" or holdout.split != "holdout":
        raise ValueError("Expected development then holdout")
    fields = (
        "seed",
        "algorithm_version",
        "dataset_sha256",
        "source_fingerprint",
        "policy_fingerprint",
    )
    metadata = {key: getattr(development, key) for key in fields}
    if any(getattr(holdout, key) != value for key, value in metadata.items()):
        raise ValueError("Split metadata mismatch")
    dev, hold = development.question_ids, holdout.question_ids
    if set(dev) & set(hold):
        raise ValueError("Development and holdout overlap")
    selected = fingerprint(sorted((*dev, *hold)))
    joint = _split_hash(metadata, dev, hold)
    if any(
        m.selected_ids_fingerprint != selected or m.split_fingerprint != joint
        for m in (development, holdout)
    ):
        raise ValueError("Split fingerprints do not match membership")


def _allocate(companies: dict, quotas: dict, seed: int) -> dict:
    """Exact small-data DP: global coverage, then within-company coverage/proportions."""
    totals = Counter(c.question_reasoning for cases in companies.values() for c in cases)
    labels = sorted((label for label, count in totals.items() if count >= 2), key=json.dumps)
    bits = {label: 1 << index for index, label in enumerate(labels)}
    full = (1 << len(bits)) - 1
    choices = {}
    for company in sorted(companies):
        counts = Counter(c.question_reasoning for c in companies[company])
        ordered = sorted(counts, key=json.dumps)
        n, h = len(companies[company]), quotas[company]
        options = []
        for values in product(*(range(min(counts[label], h) + 1) for label in ordered)):
            if sum(values) != h:
                continue
            allocation = dict(zip(ordered, values, strict=True))
            hm = sum(bits.get(label, 0) for label in ordered if allocation[label] > 0)
            dm = sum(bits.get(label, 0) for label in ordered if allocation[label] < counts[label])
            missed = sum(
                counts[label] >= 2 and allocation[label] in (0, counts[label]) for label in ordered
            )
            deviation = sum(
                (Fraction(allocation[label] * n - h * counts[label], n) ** 2 for label in ordered),
                Fraction(0),
            )
            tie = fingerprint(
                [seed, "allocation", company, [[label, allocation[label]] for label in ordered]]
            )
            options.append((hm, dm, missed, deviation, tie, allocation))
        choices[company] = options
    states = {(0, 0): (0, Fraction(0), (), ())}
    for company in sorted(companies):
        updated = {}
        for (hm, dm), (missed, deviation, ties, path) in states.items():
            for index, (new_hm, new_dm, new_missed, new_dev, tie, _) in enumerate(choices[company]):
                key = (hm | new_hm, dm | new_dm)
                proposed = (
                    missed + new_missed,
                    deviation + new_dev,
                    ties + (tie,),
                    path + ((company, index),),
                )
                if key not in updated or proposed[:3] < updated[key][:3]:
                    updated[key] = proposed
        states = updated
    if (full, full) not in states:
        raise ValueError("Requested company/reasoning coverage is infeasible")
    return {company: choices[company][index][-1] for company, index in states[(full, full)][-1]}


def freeze_splits(
    cases: tuple[BenchmarkCase, ...],
    policy: SplitPolicy,
    dataset_sha256: str,
    source_fingerprint: str,
) -> tuple[SplitManifest, SplitManifest]:
    if dataset_sha256 != policy.dataset_sha256:
        raise ValueError("Benchmark file hash differs from the approved split policy")
    if len(cases) != 52 or len({c.financebench_id for c in cases}) != 52:
        raise ValueError("Expected 52 unique selected question IDs")
    names = {company_key(name): name for name in COMPANIES}
    companies = defaultdict(list)
    for case in cases:
        if company_key(case.company) not in names:
            raise ValueError("Company outside approved split scope")
        companies[names[company_key(case.company)]].append(case)
    if set(companies) != set(COMPANIES):
        raise ValueError("All six companies are required")
    ideals = {name: Fraction(len(values) * 16, 52) for name, values in companies.items()}
    quotas = {name: value.numerator // value.denominator for name, value in ideals.items()}
    for name in sorted(
        companies, key=lambda name: (-(ideals[name] - quotas[name]), name.casefold())
    )[: 16 - sum(quotas.values())]:
        quotas[name] += 1
    if any(h < 1 or h >= len(companies[name]) for name, h in quotas.items()):
        raise ValueError("Company counts cannot support both splits")
    allocation = _allocate(companies, quotas, policy.seed)
    hold = set()
    for company in sorted(companies):
        for label, count in allocation[company].items():
            stratum = [c for c in companies[company] if c.question_reasoning == label]
            ranked = sorted(
                stratum,
                key=lambda c: (
                    fingerprint([policy.seed, "question", company, label, c.financebench_id]),
                    c.financebench_id,
                ),
            )
            hold.update(case.financebench_id for case in ranked[:count])
    development = tuple(sorted({c.financebench_id for c in cases} - hold))
    holdout = tuple(sorted(hold))
    metadata = {
        "seed": policy.seed,
        "algorithm_version": policy.algorithm_version,
        "dataset_sha256": dataset_sha256,
        "source_fingerprint": source_fingerprint,
        "policy_fingerprint": policy.fingerprint(),
    }
    common = {
        **metadata,
        "selected_ids_fingerprint": fingerprint(sorted((*development, *holdout))),
        "split_fingerprint": _split_hash(metadata, development, holdout),
    }
    dev = SplitManifest(split="development", question_ids=development, **common)
    held = SplitManifest(split="holdout", question_ids=holdout, **common)
    validate_split_pair(dev, held)
    return dev, held


def write_splits(output_dir: Path, development: SplitManifest, holdout: SplitManifest) -> None:
    validate_split_pair(development, holdout)
    destinations = [
        (output_dir / f"{manifest.split}.json", manifest) for manifest in (development, holdout)
    ]
    for path, manifest in destinations:
        if (
            path.exists()
            and SplitManifest.model_validate_json(path.read_text(encoding="utf-8")) != manifest
        ):
            raise ValueError("Refusing to overwrite a different frozen split")
    for path, manifest in destinations:
        if not path.exists():
            write_json_atomic(path, manifest.model_dump(mode="json"), indent=2)
