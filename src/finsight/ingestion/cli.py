"""Offline source-manifest and PDF extraction commands; no evaluation imports."""

import argparse
import json
from collections import Counter
from pathlib import Path

from finsight.contracts.ingestion import CorpusManifest, ExtractionConfig

from .cache import extract_cached, write_json_atomic
from .manifest import COMPANIES, build_manifest
from .qa import summarize_pages


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    manifest = commands.add_parser("manifest")
    manifest.add_argument("--metadata", type=Path, required=True)
    manifest.add_argument("--pdf-root", type=Path, required=True)
    manifest.add_argument("--output", type=Path, required=True)
    manifest.add_argument("--companies", nargs="+", default=COMPANIES)
    extraction = commands.add_parser("extract")
    extraction.add_argument("--manifest", type=Path, required=True)
    extraction.add_argument("--pdf-root", type=Path, required=True)
    extraction.add_argument("--cache-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "manifest":
            corpus = build_manifest(
                args.metadata, args.pdf_root, tuple(args.companies), "phase1-v1"
            )
            payload = corpus.model_dump(mode="json")
            if (
                args.output.exists()
                and CorpusManifest.model_validate_json(args.output.read_text(encoding="utf-8"))
                != corpus
            ):
                raise ValueError("Refusing to overwrite a different source manifest")
            write_json_atomic(args.output, payload, indent=2)
            result = {
                "documents": len(corpus.documents),
                "source_fingerprint": corpus.source_fingerprint,
                "diagnostics": [d.model_dump() for d in corpus.diagnostics],
            }
        else:
            corpus = CorpusManifest.model_validate_json(args.manifest.read_text(encoding="utf-8"))
            totals = Counter()
            for document in corpus.documents:
                totals.update(
                    summarize_pages(
                        extract_cached(args.pdf_root, document, ExtractionConfig(), args.cache_root)
                    )
                )
            result = {
                **totals,
                "documents": len(corpus.documents),
                "source_fingerprint": corpus.source_fingerprint,
            }
            print(json.dumps(result, sort_keys=True))
            return int(totals["error"] > 0)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ValueError, OSError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
