"""Native MuPDF warning/repair and exact-source encryption policy regressions."""

import pymupdf
import pytest

from finsight.contracts.ingestion import ExtractionConfig
from finsight.ingestion import pdf as adapter
from finsight.ingestion.cache import extract_cached
from finsight.ingestion.cli import main
from finsight.ingestion.fingerprints import sha256_file
from finsight.ingestion.manifest import build_manifest


def _owner_encrypted(pdf_factory, permissions):
    path = pdf_factory(texts=["Synthetic revenue 100"])
    with pymupdf.open(path) as document:
        data = document.tobytes(
            encryption=pymupdf.PDF_ENCRYPT_AES_256,
            owner_pw="synthetic-owner",
            user_pw="",
            permissions=permissions,
        )
    path.write_bytes(data)
    with pymupdf.open(path) as document:
        assert not document.needs_pass
        assert document.metadata["encryption"] is not None
    return path


def test_repaired_xref_is_rejected_by_inspection_and_manifest_cli(
    pdf_factory, metadata_factory, tmp_path
):
    path = pdf_factory(texts=["Synthetic revenue 100"])
    data = path.read_bytes()
    path.write_bytes(data[: data.index(b"xref\n")])
    with pymupdf.open(path) as document:
        assert document.is_repaired
    with pytest.raises(ValueError):
        adapter.inspect_pdf(path)
    assert (
        main(
            [
                "manifest",
                "--metadata",
                str(metadata_factory()),
                "--pdf-root",
                str(path.parent),
                "--output",
                str(tmp_path / "manifest.json"),
                "--companies",
                "AMD",
            ]
        )
        == 1
    )
    assert not (tmp_path / "manifest.json").exists()


@pytest.mark.parametrize("entrypoint", ["library", "cli"])
def test_content_stream_warnings_fail_and_are_never_cached(
    entrypoint, pdf_factory, metadata_factory, tmp_path
):
    path = pdf_factory(texts=["Synthetic revenue 100"])
    with pymupdf.open(path) as document:
        xref = document[0].get_contents()[0]
        document.update_stream(xref, document.xref_stream(xref) + b"\n[")
        document.saveIncr()
    corpus = build_manifest(metadata_factory(), path.parent, ("AMD",), "v1")
    root = tmp_path / "cache"
    if entrypoint == "library":
        pages = extract_cached(path.parent, corpus.documents[0], ExtractionConfig(), root)
        assert pages[0].extraction_status == "error"
        assert "pdf_parser_warning" in pages[0].table_diagnostics
    else:
        manifest = tmp_path / "manifest.json"
        manifest.write_text(corpus.model_dump_json(), encoding="utf-8")
        assert (
            main(
                [
                    "extract",
                    "--manifest",
                    str(manifest),
                    "--pdf-root",
                    str(path.parent),
                    "--cache-root",
                    str(root),
                ]
            )
            == 1
        )
    assert not list(root.glob("*.json"))
    healthy = pdf_factory(name="HEALTHY", texts=["Healthy text"])
    assert adapter.inspect_pdf(healthy) == 1


def test_owner_encryption_without_hash_approval_is_rejected(pdf_factory):
    path = _owner_encrypted(pdf_factory, pymupdf.PDF_PERM_COPY | pymupdf.PDF_PERM_ACCESSIBILITY)
    with pytest.raises(ValueError):
        adapter.inspect_pdf(path)


def test_approved_encryption_still_requires_copy_permission(pdf_factory, monkeypatch):
    path = _owner_encrypted(pdf_factory, 0)
    monkeypatch.setattr(
        adapter, "READABLE_ENCRYPTED_SHA256", frozenset([sha256_file(path)]), raising=False
    )
    with pytest.raises(ValueError):
        adapter.inspect_pdf(path)


def test_approved_readable_encryption_is_visible(pdf_factory, metadata_factory, monkeypatch):
    path = _owner_encrypted(pdf_factory, pymupdf.PDF_PERM_COPY | pymupdf.PDF_PERM_ACCESSIBILITY)
    monkeypatch.setattr(
        adapter, "READABLE_ENCRYPTED_SHA256", frozenset([sha256_file(path)]), raising=False
    )
    corpus = build_manifest(metadata_factory(), path.parent, ("AMD",), "v1")
    assert any(d.code == "readable_encrypted_source" for d in corpus.diagnostics)
    pages = adapter.extract_pages(path, corpus.documents[0], ExtractionConfig())
    assert pages[0].extraction_status == "ok"
    assert "readable_encrypted_source" in pages[0].table_diagnostics


def test_actualtext_position_warning_preserves_available_text_with_visible_gap(
    pdf_factory, metadata_factory, tmp_path
):
    path = pdf_factory(texts=["Synthetic revenue 100"])
    with pymupdf.open(path) as document:
        xref = document[0].get_contents()[0]
        document.update_stream(
            xref,
            b"/Span << /ActualText (Unpositioned replacement) >> BDC EMC\n"
            + document.xref_stream(xref),
        )
        document.saveIncr()
    corpus = build_manifest(metadata_factory(), path.parent, ("AMD",), "v1")
    pages = extract_cached(path.parent, corpus.documents[0], ExtractionConfig(), tmp_path / "cache")
    assert pages[0].extraction_status == "ok"
    assert pages[0].text == "Synthetic revenue 100\n"
    assert "actualtext_position_warning" in pages[0].table_diagnostics
    assert len(list((tmp_path / "cache").glob("*.json"))) == 1
