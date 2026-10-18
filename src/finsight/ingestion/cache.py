"""Validated, atomic per-document page cache. No benchmark inputs."""

import json
import os
import tempfile
from pathlib import Path
from typing import Literal

from finsight.contracts.base import Contract, NonBlank, PositiveInt, Sha256, fingerprint
from finsight.contracts.documents import DocumentManifest, Page
from finsight.contracts.ingestion import ExtractionConfig

from .fingerprints import sha256_file
from .manifest import safe_pdf_path
from .pdf import extract_pages, parser_versions


class _CachedPages(Contract):
    schema_version: Literal["1"] = "1"
    document_id: NonBlank
    pdf_sha256: Sha256
    config_fingerprint: Sha256
    versions: dict[str, str]
    page_count: PositiveInt
    payload_fingerprint: Sha256
    pages: tuple[Page, ...]


def write_json_atomic(path: Path, payload: object, *, indent: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(
                payload,
                handle,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
                indent=indent,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def cache_path(document: DocumentManifest, config: ExtractionConfig, cache_root: Path) -> Path:
    key = fingerprint(
        {
            "schema": "1",
            "document_id": document.document_id,
            "pdf": document.sha256,
            "config": config.fingerprint(),
            "versions": parser_versions(),
        }
    )
    return cache_root / f"{key}.json"


def load_cached(
    document: DocumentManifest, config: ExtractionConfig, cache_root: Path
) -> tuple[Page, ...]:
    """Read and validate frozen pages without re-extracting or accepting annotations."""
    destination = cache_path(document, config, cache_root)
    versions = parser_versions()
    cached = _CachedPages.model_validate_json(destination.read_text(encoding="utf-8"))
    valid = (
        cached.document_id == document.document_id
        and cached.pdf_sha256 == document.sha256
        and cached.config_fingerprint == config.fingerprint()
        and cached.versions == versions
        and cached.page_count == document.page_count
        and len(cached.pages) == document.page_count
        and all(
            p.document_id == document.document_id
            and p.page_index == i
            and p.extraction_status != "error"
            for i, p in enumerate(cached.pages)
        )
        and cached.payload_fingerprint
        == fingerprint([p.model_dump(mode="json") for p in cached.pages])
    )
    if not valid:
        raise ValueError("Cached page identity, completeness, or payload integrity mismatch")
    return cached.pages


def extract_cached(
    pdf_root: Path, document: DocumentManifest, config: ExtractionConfig, cache_root: Path
) -> tuple[Page, ...]:
    pdf = safe_pdf_path(pdf_root, document.local_path)
    if sha256_file(pdf) != document.sha256:
        raise ValueError("Source PDF hash changed; refusing cached pages")
    destination = cache_path(document, config, cache_root)
    versions = parser_versions()
    try:
        return load_cached(document, config, cache_root)
    except (ValueError, OSError):
        pass  # Rebuild from the verified source, never from benchmark annotations.
    pages = extract_pages(pdf, document, config)
    if any(page.extraction_status == "error" for page in pages):
        return pages  # Preserve errors for the caller, but never cache a failed extraction.
    envelope = _CachedPages(
        document_id=document.document_id,
        pdf_sha256=document.sha256,
        config_fingerprint=config.fingerprint(),
        versions=versions,
        page_count=document.page_count,
        payload_fingerprint=fingerprint([p.model_dump(mode="json") for p in pages]),
        pages=pages,
    )
    write_json_atomic(destination, envelope.model_dump(mode="json"))
    return pages
