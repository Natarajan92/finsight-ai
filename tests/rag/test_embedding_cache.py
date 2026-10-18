"""Embedding cache identities distinguish submission roles and configuration."""

import json

import pytest

from finsight.runtime.errors import FinsightError


def test_roles_and_material_config_change_cache_key(embedding_setup):
    backend, cache, _, _, _ = embedding_setup
    assert cache.key("same text", role="query") != cache.key("same text", role="document")
    changed = type(cache)(
        cache.root, backend.config.model_copy(update={"embedding_revision": "changed"})
    )
    assert cache.key("same", role="document") != changed.key("same", role="document")


def test_tampered_cache_is_rejected(embedding_setup):
    backend, cache, _, _, _ = embedding_setup
    backend.embed_documents(["one"])
    path = cache.root / (cache.key("one", role="document") + ".json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["vector"][0] = 0.99
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(FinsightError, match="embedding_cache_integrity"):
        backend.embed_documents(["one"])
