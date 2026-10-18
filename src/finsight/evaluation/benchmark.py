"""Offline-only FinanceBench questions and annotations. Never import from runtime."""

from pathlib import Path

from pydantic import model_validator

from finsight.contracts.base import Contract, NonBlank, PageIndex
from finsight.contracts.ingestion import CorpusManifest
from finsight.ingestion.manifest import company_key


class BenchmarkEvidence(Contract):
    doc_name: NonBlank
    evidence_page_num: PageIndex
    evidence_text: NonBlank
    evidence_text_full_page: str


class BenchmarkCase(Contract):
    financebench_id: NonBlank
    company: NonBlank
    doc_name: NonBlank
    question_type: NonBlank
    question_reasoning: str | None
    domain_question_num: str | None
    question: NonBlank
    answer: NonBlank
    justification: str | None
    dataset_subset_label: NonBlank
    evidence: tuple[BenchmarkEvidence, ...]

    @model_validator(mode="after")
    def evidence_present(self):
        if not self.evidence:
            raise ValueError("A benchmark case requires evidence annotations")
        return self


def load_benchmark(path: Path, corpus: CorpusManifest) -> tuple[BenchmarkCase, ...]:
    documents = {doc.doc_name: doc for doc in corpus.documents}
    selected = {company_key(doc.company) for doc in corpus.documents if doc.company is not None}
    seen = set()
    cases = []
    for line in path.read_text(encoding="utf-8").splitlines():
        case = BenchmarkCase.model_validate_json(line)
        if case.financebench_id in seen:
            raise ValueError("Duplicate benchmark question ID")
        seen.add(case.financebench_id)
        if company_key(case.company) not in selected:
            continue
        document = documents.get(case.doc_name)
        if document is None or company_key(document.company or "") != company_key(case.company):
            raise ValueError("Question-to-document join is missing or has a different company")
        for evidence in case.evidence:
            source = documents.get(evidence.doc_name)
            if source is None or evidence.evidence_page_num >= source.page_count:
                raise ValueError("Evidence document/page is outside the approved corpus")
        cases.append(case)
    return tuple(sorted(cases, key=lambda case: case.financebench_id))
