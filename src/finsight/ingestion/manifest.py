"""Offline document-information join. No question/answer JSON is accepted."""

import json
from collections import defaultdict
from pathlib import Path

from finsight.contracts.documents import DocumentManifest
from finsight.contracts.ingestion import AuditDiagnostic, CorpusManifest, validate_relative_path

from .fingerprints import document_id, sha256_file, source_fingerprint
from .pdf import inspect_pdf

COMPANIES = ("AMD", "American Express", "PepsiCo", "Boeing", "Amcor", "Johnson & Johnson")
_METADATA_FIELDS = {"doc_name", "company", "gics_sector", "doc_type", "doc_period", "doc_link"}


def company_key(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def safe_pdf_path(root: Path, relative: str) -> Path:
    validate_relative_path(relative)
    resolved_root = root.resolve()
    path = (resolved_root / relative).resolve()
    if not path.is_relative_to(resolved_root) or not path.is_file():
        raise ValueError("PDF path escapes root or is not a file")
    return path


def build_manifest(
    metadata_path: Path, pdf_root: Path, companies: tuple[str, ...], ingestion_version: str
) -> CorpusManifest:
    selected = {company_key(name) for name in companies}
    if not selected or len(selected) != len(companies):
        raise ValueError("Select distinct companies")
    records = {}
    diagnostics = []
    for line in metadata_path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if not isinstance(record, dict) or set(record) != _METADATA_FIELDS:
            raise ValueError("Expected document-information fields only")
        name, company = record["doc_name"], record["company"]
        if not isinstance(name, str) or not isinstance(company, str):
            raise ValueError("Document name and company must be strings")
        if name in records and records[name] != record:
            if {company_key(company), company_key(records[name]["company"])} & selected:
                raise ValueError(f"Conflicting selected metadata: {name}")
            diagnostics.append(
                AuditDiagnostic(
                    code="outside_metadata_conflict",
                    message="Conflicting metadata outside selected corpus",
                    doc_names=(name,),
                )
            )
        else:
            records[name] = record
    paths = defaultdict(list)
    for path in sorted(pdf_root.rglob("*.pdf")):
        paths[path.stem].append(path)
    documents = []
    present_companies = set()
    for name, record in sorted(records.items()):
        if company_key(record["company"]) not in selected:
            continue
        if Path(name).name != name or any(c in name for c in ("/", "\\", ":")):
            raise ValueError("Unsafe document name")
        if len(paths[name]) != 1:
            raise ValueError(f"Expected exactly one matching PDF: {name}")
        relative = paths[name][0].relative_to(pdf_root).as_posix()
        path = safe_pdf_path(pdf_root, relative)
        digest = sha256_file(path)
        page_count = inspect_pdf(path)
        if sha256_file(path) != digest:
            raise ValueError(f"PDF changed during inspection: {name}")
        period = record["doc_period"]
        if period is not None and (isinstance(period, bool) or not isinstance(period, (str, int))):
            raise ValueError("Invalid fiscal period")
        documents.append(
            DocumentManifest(
                document_id=document_id(name, digest),
                doc_name=name,
                company=record["company"],
                fiscal_period=None if period is None else str(period),
                filing_type=record["doc_type"],
                source_url=record["doc_link"],
                local_path=relative,
                sha256=digest,
                page_count=page_count,
                ingestion_version=ingestion_version,
            )
        )
        present_companies.add(company_key(record["company"]))
    if present_companies != selected:
        raise ValueError("Some selected companies have no metadata-matched PDF")
    by_hash = defaultdict(list)
    for document in documents:
        by_hash[document.sha256].append(document.doc_name)
    for name in sorted(set(paths) - records.keys()):
        for candidate in paths[name]:
            relative = candidate.relative_to(pdf_root).as_posix()
            digest = sha256_file(safe_pdf_path(pdf_root, relative))
            canonical = by_hash.get(digest, [])
            if len(canonical) > 1:
                raise ValueError("Alias hash matches multiple canonical documents")
            if canonical:
                diagnostics.append(
                    AuditDiagnostic(
                        code="duplicate_alias",
                        message=f"Excluded byte-identical alias: {relative}",
                        doc_names=(name, canonical[0]),
                    )
                )
    return CorpusManifest(
        documents=tuple(documents),
        metadata_sha256=sha256_file(metadata_path),
        source_fingerprint=source_fingerprint([[d.doc_name, d.sha256] for d in documents]),
        diagnostics=tuple(diagnostics),
    )
