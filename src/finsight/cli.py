"""Installed baseline CLI. Paid commands require explicit opt-in and local guards."""

import argparse
import json
from pathlib import Path

from finsight.application import error_answer
from finsight.config import Settings
from finsight.contracts import BaselineConfig, QueryRequest
from finsight.runtime.errors import FinsightError
from finsight.runtime.ports import load_baseline_config


def _common(parser):
    parser.add_argument(
        "--config", type=Path, default=Path("configs/runtime/phase-2-baseline.json")
    )
    for flag in (
        "manifest",
        "pdf-root",
        "page-cache",
        "tokenizer-dir",
        "embedding-cache",
        "index-root",
        "rates",
        "ledger",
        "trace-root",
        "env-file",
    ):
        parser.add_argument("--" + flag, type=Path)


def _settings(args) -> Settings:
    fields = {
        "manifest": "manifest_path",
        "pdf_root": "source_pdf_dir",
        "page_cache": "page_cache_root",
        "tokenizer_dir": "tokenizer_dir",
        "embedding_cache": "embedding_cache_root",
        "index_root": "index_root",
        "rates": "rates_path",
        "ledger": "ledger_path",
        "trace_root": "trace_root",
    }
    values = {
        field: getattr(args, arg)
        for arg, field in fields.items()
        if getattr(args, arg, None) is not None
    }
    if getattr(args, "env_file", None) is not None:
        values["_env_file"] = args.env_file
    return Settings(**values)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="finsight-rag", description="Evidence-first baseline RAG")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare-tokenizer", "preflight", "budget-init", "build-index", "ask"):
        child = commands.add_parser(name)
        _common(child)
        if name in {"build-index", "ask"}:
            child.add_argument("--allow-paid", action="store_true")
        if name == "preflight":
            child.add_argument("--check-providers", action="store_true")
        if name == "ask":
            child.add_argument("--question", required=True)
            child.add_argument("--company")
            child.add_argument("--period")
            child.add_argument("--document-id", action="append")
            child.add_argument("--top-k", type=int, default=5)
    synthetic = commands.add_parser("smoke")
    synthetic.add_argument("--synthetic", action="store_true", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "smoke":
            from finsight.rag_smoke import run_rag_smoke

            print(json.dumps(run_rag_smoke(), sort_keys=True))
            return 0
        settings = _settings(args)
        if args.command == "budget-init":
            from finsight.observability.budget import BudgetLedger

            ledger = BudgetLedger.initialize(
                settings.ledger_path,
                BaselineConfig().budget_id,
                anchor_path=settings.budget_anchor_path,
                activity_roots=(
                    settings.index_root,
                    settings.embedding_cache_root,
                    settings.trace_root,
                ),
            )
            result = ledger.snapshot().model_dump(mode="json")
        else:
            config = load_baseline_config(args.config)
            if args.command == "prepare-tokenizer":
                from finsight.chunking.tokenizer import prepare_tokenizer

                artifact = prepare_tokenizer(settings.tokenizer_dir, config.tokenizer_revision)
                result = artifact.model_dump(mode="json", exclude={"directory"})
            elif args.command == "preflight":
                from finsight.runtime.factory import preflight, verify_provider_models

                result = preflight(settings, config)
                if args.check_providers:
                    result["providers"] = verify_provider_models(settings, config)
                print(json.dumps(result, sort_keys=True))
                return 0 if result["status"] == "ready" else 1
            elif args.command == "build-index":
                from finsight.runtime.factory import build_local_index

                manifest = build_local_index(settings, config, allow_paid=args.allow_paid)
                result = dict(
                    status="complete",
                    index_fingerprint=manifest.fingerprint(),
                    chunks=manifest.chunk_count,
                    source_fingerprint=manifest.source_fingerprint,
                )
            else:
                from finsight.runtime.factory import create_application

                request = QueryRequest(
                    question=args.question,
                    company=args.company,
                    period=args.period,
                    document_ids=tuple(args.document_id) if args.document_id else None,
                    top_k=args.top_k,
                )
                service = create_application(settings, config, allow_paid=args.allow_paid)
                try:
                    answer = service.answer(request)
                    print(
                        json.dumps(
                            dict(
                                answer=answer.model_dump(mode="json"),
                                trace_id=service.last_trace_id,
                            ),
                            sort_keys=True,
                        )
                    )
                    return 1 if answer.status == "error" else 0
                finally:
                    service.close()
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as exc:
        code = exc.code if isinstance(exc, FinsightError) else "invalid_configuration"
        answer = error_answer(code)
        result = (
            dict(answer=answer.model_dump(mode="json"), trace_id=None)
            if args.command == "ask"
            else dict(error=answer.error.model_dump(mode="json"))
        )
        print(json.dumps(result, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
