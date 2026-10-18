"""Source identity helpers; independent of evaluation labels."""

import hashlib
from pathlib import Path

from finsight.contracts.base import fingerprint


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def document_id(doc_name: str, pdf_sha256: str) -> str:
    return "doc_" + fingerprint([doc_name, pdf_sha256])


def source_fingerprint(pairs: list[list[str]]) -> str:
    return fingerprint(sorted(pairs))
