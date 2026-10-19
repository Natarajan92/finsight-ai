"""Development-only AMD evaluation. New requests require an explicit paid flag."""

import argparse
import json
from decimal import Decimal
from pathlib import Path

from finsight.config import Settings
from finsight.runtime.errors import FinsightError
from finsight.runtime.experiment_factory import create_experiment_lab

from .campaign import load_run, plan_evaluation, run_evaluation
from .reporting import write_reports


def main(argv=None):
    parser = argparse.ArgumentParser(prog="finsight-evaluate", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "run"):
        command = sub.add_parser(name)
        command.add_argument(
            "--questions",
            type=Path,
            default=Path("source-data/data/financebench_open_source.jsonl"),
        )
        command.add_argument("--split-dir", type=Path, default=Path("configs/evaluation"))
        command.add_argument(
            "--arms",
            default="A",
            help="Unique selected arms, e.g. A or ABCD; no automatic fallback",
        )
        command.add_argument("--max-cost-usd", type=Decimal, default=Decimal("0.25"))
        if name == "run":
            command.add_argument("--allow-paid", action="store_true")
            command.add_argument("--output", type=Path, default=Path("results/phase-4-amd"))
    report = sub.add_parser("report")
    report.add_argument("--run", type=Path, required=True)
    report.add_argument("--output", type=Path, default=Path("results/phase-4-amd"))
    report.add_argument("--review", type=Path)
    args = parser.parse_args(argv)
    lab = None
    try:
        if args.command == "report":
            run = load_run(args.run)
            paths = write_reports(run, args.output, review=args.review)
            print(
                json.dumps(
                    dict(
                        status="complete" if run.complete else "incomplete",
                        reports=[str(p) for p in paths["public"]],
                    )
                )
            )
            return 0 if run.complete else 1
        lab = create_experiment_lab(Settings(), doc_name="AMD_2022_10K")
        if args.command == "plan":
            plan = plan_evaluation(
                lab, args.questions, args.split_dir, arms=args.arms, max_cost_usd=args.max_cost_usd
            )
            print(json.dumps(plan, sort_keys=True))
            return 0 if plan["status"] == "ready" else 1
        run = run_evaluation(
            lab,
            args.questions,
            args.split_dir,
            Path("data/evaluation/phase4"),
            arms=args.arms,
            max_cost_usd=args.max_cost_usd,
            allow_paid=args.allow_paid,
        )
        paths = write_reports(run, args.output)
        print(
            json.dumps(
                dict(
                    status="complete" if run.complete else "incomplete",
                    run_id=run.identity,
                    records=len(run.records),
                    expected_records=run.expected_records,
                    replay=run.replay,
                    new_cost_usd=str(run.new_cost_usd) if run.new_cost_usd is not None else None,
                    reports=[str(p) for p in paths["public"]],
                )
            )
        )
        return 0 if run.complete else 1
    except Exception as exc:
        # Annotation validation errors can contain complete gold fields: never echo them.
        code = exc.code if isinstance(exc, FinsightError) else "evaluation_configuration"
        print(json.dumps(dict(status="error", code=code)))
        return 1
    finally:
        if lab is not None:
            lab.close()


if __name__ == "__main__":
    raise SystemExit(main())
