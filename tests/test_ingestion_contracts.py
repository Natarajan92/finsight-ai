import pytest
from pydantic import ValidationError

from finsight.contracts.ingestion import CorpusManifest, ExtractionConfig
from finsight.ingestion.manifest import build_manifest


def test_manifest_schema_and_roundtrip(pdf_factory, metadata_factory):
    path = pdf_factory()
    manifest = build_manifest(metadata_factory(), path.parent, ("AMD",), "v1")
    assert CorpusManifest.model_validate_json(manifest.model_dump_json()) == manifest
    assert CorpusManifest.model_json_schema() and ExtractionConfig.model_json_schema()
    assert len(ExtractionConfig().fingerprint()) == 64


@pytest.mark.parametrize("mutation", ["fingerprint", "duplicate", "identity", "path", "empty"])
def test_manifest_rejects_inconsistent_provenance(mutation, pdf_factory, metadata_factory):
    path = pdf_factory()
    payload = build_manifest(metadata_factory(), path.parent, ("AMD",), "v1").model_dump()
    if mutation == "fingerprint":
        payload["source_fingerprint"] = "0" * 64
    elif mutation == "duplicate":
        payload["documents"] *= 2
    elif mutation == "identity":
        payload["documents"][0]["document_id"] = "unrelated"
    elif mutation == "path":
        payload["documents"][0]["local_path"] = "../outside.pdf"
    else:
        payload["documents"] = []
    with pytest.raises(ValidationError):
        CorpusManifest.model_validate(payload)


def test_config_rejects_gold_and_reordering():
    for payload in [{"gold_answer": "injected"}, {"sort": True}, {"text_flags": -1}]:
        with pytest.raises(ValidationError):
            ExtractionConfig.model_validate(payload)
