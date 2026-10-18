"""Offline development extraction diagnostics, separate from RAG accuracy."""

import unicodedata
from collections import Counter
from pathlib import Path

from finsight.contracts.ingestion import CorpusManifest, ExtractionConfig
from finsight.ingestion.cache import load_cached
from finsight.ingestion.manifest import COMPANIES, company_key

from .benchmark import BenchmarkCase
from .splits import SplitManifest, SplitPolicy, freeze_splits, validate_split_pair


def normalize_quote(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def audit_benchmark(
    cases: tuple[BenchmarkCase, ...],
    corpus: CorpusManifest,
    development: SplitManifest,
    holdout: SplitManifest,
    cache_root: Path,
) -> tuple[dict, list[dict]]:
    validate_split_pair(development, holdout)
    if corpus.source_fingerprint != development.source_fingerprint:
        raise ValueError("Split belongs to a different source corpus")
    if {case.financebench_id for case in cases} != set(
        (*development.question_ids, *holdout.question_ids)
    ):
        raise ValueError("Benchmark IDs differ from frozen membership")
    policy = SplitPolicy(dataset_sha256=development.dataset_sha256)
    expected = freeze_splits(cases, policy, development.dataset_sha256, corpus.source_fingerprint)
    if expected != (development, holdout):
        raise ValueError("Frozen membership differs from deterministic split policy")
    documents = {document.doc_name: document for document in corpus.documents}
    dev_ids = set(development.question_ids)
    cached = {}
    details = []
    for case in cases:
        if case.financebench_id not in dev_ids:
            continue
        for evidence in case.evidence:
            if evidence.doc_name not in cached:
                cached[evidence.doc_name] = load_cached(
                    documents[evidence.doc_name], ExtractionConfig(), cache_root
                )
            page = cached[evidence.doc_name][evidence.evidence_page_num]
            details.append(
                {
                    "question_id": case.financebench_id,
                    "doc_name": evidence.doc_name,
                    "page_index": evidence.evidence_page_num,
                    "normalized_exact_match": normalize_quote(evidence.evidence_text)
                    in normalize_quote(page.text),
                    "extraction_status": page.extraction_status,
                }
            )
    company_distribution = []
    for name in COMPANIES:
        company_cases = [case for case in cases if company_key(case.company) == company_key(name)]
        company_documents = [
            d for d in corpus.documents if company_key(d.company or "") == company_key(name)
        ]
        development_count = sum(case.financebench_id in dev_ids for case in company_cases)
        company_distribution.append(
            {
                "company": name,
                "filings": len(company_documents),
                "pages": sum(d.page_count for d in company_documents),
                "questions": len(company_cases),
                "development": development_count,
                "holdout": len(company_cases) - development_count,
            }
        )
    counts = Counter(case.question_reasoning for case in cases)
    reasoning = []
    for label in sorted(counts, key=lambda x: (x is None, x or "")):
        dev = sum(
            case.question_reasoning == label and case.financebench_id in dev_ids for case in cases
        )
        reasoning.append(
            {
                "reasoning": label,
                "total": counts[label],
                "development": dev,
                "holdout": counts[label] - dev,
            }
        )
    references = [e for case in cases for e in case.evidence]
    summary = {
        "selected_questions": len(cases),
        "question_linked_filings": len({c.doc_name for c in cases}),
        "evidence_references": len(references),
        "distinct_evidence_pages": len({(e.doc_name, e.evidence_page_num) for e in references}),
        "development_evidence_references": len(details),
        "development_normalized_exact_matches": sum(
            row["normalized_exact_match"] for row in details
        ),
        "source_fingerprint": corpus.source_fingerprint,
        "dataset_sha256": development.dataset_sha256,
        "split_fingerprint": development.split_fingerprint,
        "company_distribution": company_distribution,
        "reasoning_distribution": reasoning,
        "scope": "Unseen questions, not unseen documents; filings may appear in both splits.",
        "diagnostic_note": (
            "Quote matching is a mechanical extraction check, not RAG accuracy or faithfulness."
        ),
    }
    return summary, details
