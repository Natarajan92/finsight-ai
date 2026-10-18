import json

import pytest

from finsight.contracts.ingestion import ExtractionConfig
from finsight.ingestion import cache
from finsight.ingestion.manifest import build_manifest


def setup_cache(pdf_factory, metadata_factory, tmp_path):
    path = pdf_factory()
    document = build_manifest(metadata_factory(), path.parent, ("AMD",), "v1").documents[0]
    root = tmp_path / "cache"
    pages = cache.extract_cached(path.parent, document, ExtractionConfig(), root)
    return path, document, root, pages


def test_cache_hit_never_calls_parser(pdf_factory, metadata_factory, tmp_path, monkeypatch):
    path, document, root, pages = setup_cache(pdf_factory, metadata_factory, tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("parser called on cache hit")

    monkeypatch.setattr(cache, "extract_pages", forbidden)
    assert cache.extract_cached(path.parent, document, ExtractionConfig(), root) == pages


def test_read_only_cache_access_validates_complete_identity(
    pdf_factory, metadata_factory, tmp_path
):
    _, document, root, pages = setup_cache(pdf_factory, metadata_factory, tmp_path)
    assert cache.load_cached(document, ExtractionConfig(), root) == pages
    with pytest.raises(ValueError):
        cache.load_cached(document.model_copy(update={"page_count": 3}), ExtractionConfig(), root)


@pytest.mark.parametrize("corruption", ["truncated", "identity", "missing_page", "text", "version"])
def test_corrupt_cache_rebuilt(corruption, pdf_factory, metadata_factory, tmp_path):
    path, document, root, pages = setup_cache(pdf_factory, metadata_factory, tmp_path)
    file = next(root.glob("*.json"))
    payload = json.loads(file.read_text())
    if corruption == "truncated":
        file.write_text("{")
    else:
        if corruption == "identity":
            payload["document_id"] = "unrelated"
        elif corruption == "missing_page":
            payload["pages"].pop()
        elif corruption == "text":
            payload["pages"][0]["text"] = "corrupt"
        else:
            payload["schema_version"] = "old"
        file.write_text(json.dumps(payload))
    assert cache.extract_cached(path.parent, document, ExtractionConfig(), root) == pages


def test_config_and_backend_invalidate_cache(pdf_factory, metadata_factory, tmp_path, monkeypatch):
    path, document, root, _ = setup_cache(pdf_factory, metadata_factory, tmp_path)
    cache.extract_cached(path.parent, document, ExtractionConfig(extractor_version="v2"), root)
    cache.extract_cached(path.parent, document, ExtractionConfig(text_flags=3), root)
    monkeypatch.setattr(cache, "parser_versions", lambda: {"pymupdf": "future", "mupdf": "future"})
    cache.extract_cached(path.parent, document, ExtractionConfig(), root)
    assert len(list(root.glob("*.json"))) == 4


def test_changed_source_not_hidden_by_cache(pdf_factory, metadata_factory, tmp_path):
    path, document, root, _ = setup_cache(pdf_factory, metadata_factory, tmp_path)
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="hash"):
        cache.extract_cached(path.parent, document, ExtractionConfig(), root)


def test_interrupted_write_does_not_replace_cache(
    pdf_factory, metadata_factory, tmp_path, monkeypatch
):
    path = pdf_factory()
    document = build_manifest(metadata_factory(), path.parent, ("AMD",), "v1").documents[0]

    def interrupted(*args):
        raise OSError("synthetic interrupted replace")

    monkeypatch.setattr(cache.os, "replace", interrupted)
    with pytest.raises(OSError):
        cache.extract_cached(path.parent, document, ExtractionConfig(), tmp_path / "cache")
    assert not list((tmp_path / "cache").glob("*.json"))
    assert not list((tmp_path / "cache").glob("*.tmp"))
