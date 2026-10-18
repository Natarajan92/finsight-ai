"""Runtime source contracts: no benchmark questions or annotations."""

from pathlib import PurePosixPath, PureWindowsPath
from typing import Literal, Self

from pydantic import model_validator

from .base import Contract, NonBlank, NonnegativeInt, Sha256, fingerprint
from .documents import DocumentManifest


def validate_relative_path(value: str) -> str:
    path = PurePosixPath(value)
    if (
        "\\" in value
        or path.is_absolute()
        or PureWindowsPath(value).drive
        or ".." in path.parts
        or not path.parts
        or path.as_posix() != value
    ):
        raise ValueError("Source path must be a normalized relative POSIX path")
    return value


class AuditDiagnostic(Contract):
    code: Literal["duplicate_alias", "outside_metadata_conflict"]
    message: NonBlank
    doc_names: tuple[NonBlank, ...] = ()


class ExtractionConfig(Contract):
    schema_version: Literal["1"] = "1"
    extractor_version: NonBlank = "phase1-v1"
    sort: Literal[False] = False
    text_flags: NonnegativeInt = 195  # PyMuPDF 1.28.2 TEXTFLAGS_TEXT.

    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


class CorpusManifest(Contract):
    schema_version: Literal["1"] = "1"
    documents: tuple[DocumentManifest, ...]
    metadata_sha256: Sha256
    source_fingerprint: Sha256
    diagnostics: tuple[AuditDiagnostic, ...] = ()

    @model_validator(mode="after")
    def consistent_sources(self) -> Self:
        if not self.documents:
            raise ValueError("Corpus must contain documents")
        for key in ("document_id", "doc_name", "local_path"):
            values = [getattr(doc, key) for doc in self.documents]
            if len(set(values)) != len(values):
                raise ValueError(f"Duplicate {key}")
        pairs = []
        for doc in self.documents:
            validate_relative_path(doc.local_path)
            if doc.document_id != "doc_" + fingerprint([doc.doc_name, doc.sha256]):
                raise ValueError("Document identity does not match source hash/name")
            pairs.append([doc.doc_name, doc.sha256])
        if fingerprint(sorted(pairs)) != self.source_fingerprint:
            raise ValueError("Source fingerprint does not match canonical document pairs")
        return self
