"""Offline benchmark preparation. No retrieval, generation, or holdout evaluation."""

import argparse
import json
from pathlib import Path

from finsight.contracts.ingestion import CorpusManifest
from finsight.ingestion.cache import write_json_atomic
from finsight.ingestion.fingerprints import sha256_file

from .audit import audit_benchmark
from .benchmark import load_benchmark
from .splits import SplitManifest, SplitPolicy, freeze_splits, write_splits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("split", "validate"):
        command = commands.add_parser(name)
        command.add_argument("--questions", type=Path, required=True)
        command.add_argument("--manifest", type=Path, required=True)
        if name == "split":
            command.add_argument("--policy", type=Path, required=True)
            command.add_argument("--output-dir", type=Path, required=True)
        else:
            command.add_argument("--split-dir", type=Path, required=True)
            command.add_argument("--split", choices=["development"], required=True)
            command.add_argument("--cache-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        corpus = CorpusManifest.model_validate_json(args.manifest.read_text(encoding="utf-8"))
        cases = load_benchmark(args.questions, corpus)
        dataset_sha256 = sha256_file(args.questions)
        if args.command == "split":
            policy = SplitPolicy.model_validate_json(args.policy.read_text(encoding="utf-8"))
            stored = args.output_dir / "split-policy.json"
            if (
                stored.exists()
                and SplitPolicy.model_validate_json(stored.read_text(encoding="utf-8")) != policy
            ):
                raise ValueError("Refusing a different frozen split policy")
            dev, hold = freeze_splits(cases, policy, dataset_sha256, corpus.source_fingerprint)
            write_splits(args.output_dir, dev, hold)
            if not stored.exists():
                write_json_atomic(stored, policy.model_dump(mode="json"), indent=2)
            result = {
                "development": len(dev.question_ids),
                "holdout": len(hold.question_ids),
                "split_fingerprint": dev.split_fingerprint,
            }
        else:
            dev = SplitManifest.model_validate_json(
                (args.split_dir / "development.json").read_text(encoding="utf-8")
            )
            hold = SplitManifest.model_validate_json(
                (args.split_dir / "holdout.json").read_text(encoding="utf-8")
            )
            policy = SplitPolicy.model_validate_json(
                (args.split_dir / "split-policy.json").read_text(encoding="utf-8")
            )
            if (
                dataset_sha256 != dev.dataset_sha256
                or policy.fingerprint() != dev.policy_fingerprint
            ):
                raise ValueError("Dataset or policy changed after the split was frozen")
            result, details = audit_benchmark(cases, corpus, dev, hold, args.cache_root)
            write_json_atomic(
                Path("data/evaluation/development-extraction.json"),
                {"summary": result, "development_only_details": details},
                indent=2,
            )
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ValueError, OSError) as exc:
        # Raw validation errors can include gold field values. Report only their type.
        print(json.dumps({"status": "error", "error_type": type(exc).__name__}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
