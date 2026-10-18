"""Synthetic source joins; original FinanceBench files are never test fixtures."""

import json
import shutil

import pytest

from finsight.ingestion.fingerprints import document_id, sha256_file
from finsight.ingestion.manifest import build_manifest, safe_pdf_path
from finsight.ingestion.pdf import inspect_pdf


def test_exact_join_alias_hashes_and_portability(pdf_factory, metadata_factory):
    path = pdf_factory()
    shutil.copyfile(path, path.with_name("AMD_duplicate.pdf"))
    manifest = build_manifest(metadata_factory(), path.parent, ("AMD",), "phase1-v1")
    doc = manifest.documents[0]
    assert doc.doc_name == "AMD_2022_10K" and doc.page_count == 2
    assert doc.document_id == document_id(doc.doc_name, sha256_file(path))
    assert doc.local_path == path.name
    assert (doc.fiscal_period, doc.filing_type, doc.source_url) == ("2022", "10K", None)
    assert len(manifest.documents) == 1
    assert manifest.diagnostics[0].code == "duplicate_alias"
    repeated = build_manifest(metadata_factory(), path.parent, ("AMD",), "phase1-v1")
    assert repeated == manifest


def test_missing_metadata_is_explicit(pdf_factory, metadata_factory):
    path = pdf_factory()
    records = [
        {
            "doc_name": path.stem,
            "company": "AMD",
            "doc_type": None,
            "doc_period": None,
            "doc_link": None,
            "gics_sector": None,
        }
    ]
    doc = build_manifest(metadata_factory(records), path.parent, ("AMD",), "v1").documents[0]
    assert doc.filing_type is None and doc.fiscal_period is None


@pytest.mark.parametrize("mutation", ["missing", "conflict", "duplicate_pdf", "unsafe_name"])
def test_unresolved_selected_sources_fail(mutation, pdf_factory, metadata_factory):
    path = pdf_factory()
    metadata = metadata_factory()
    row = json.loads(metadata.read_text())
    if mutation == "missing":
        path.unlink()
    elif mutation == "conflict":
        metadata.write_text(json.dumps(row) + "\n" + json.dumps({**row, "doc_period": 2021}))
    elif mutation == "duplicate_pdf":
        nested = path.parent / "nested"
        nested.mkdir()
        shutil.copyfile(path, nested / path.name)
    else:
        metadata.write_text(json.dumps({**row, "doc_name": "../outside"}))
    with pytest.raises(ValueError):
        build_manifest(metadata, path.parent, ("AMD",), "v1")


def test_outside_conflicts_reported_without_expansion(pdf_factory, metadata_factory):
    path = pdf_factory()
    selected = json.loads(metadata_factory().read_text())
    other = {**selected, "doc_name": "OTHER_2023", "company": "Other", "doc_period": 2023}
    metadata = metadata_factory([selected, other, {**other, "doc_period": 2022}])
    manifest = build_manifest(metadata, path.parent, ("AMD",), "v1")
    assert len(manifest.documents) == 1
    assert any(d.code == "outside_metadata_conflict" for d in manifest.diagnostics)


@pytest.mark.parametrize(
    "relative", ["../outside.pdf", "/absolute.pdf", "C:/outside.pdf", "a\\b.pdf"]
)
def test_paths_cannot_escape_root(tmp_path, relative):
    with pytest.raises(ValueError):
        safe_pdf_path(tmp_path, relative)


def test_resolved_link_cannot_escape(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(b"outside")
    try:
        (root / "escape.pdf").symlink_to(outside)
    except OSError:
        pytest.skip("Creating symlinks is unavailable on this host")
    with pytest.raises(ValueError):
        safe_pdf_path(root, "escape.pdf")


def test_invalid_and_encrypted_pdfs_fail(pdf_factory):
    encrypted = pdf_factory(password="synthetic-password")
    with pytest.raises(ValueError):
        inspect_pdf(encrypted)
    encrypted.write_bytes(b"not a PDF")
    with pytest.raises(ValueError):
        inspect_pdf(encrypted)
