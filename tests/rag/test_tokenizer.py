"""Genuine local BPE offsets, with no hosted model download or fallback."""

import importlib
import json
from hashlib import sha256

import pytest

from finsight.contracts import BaselineConfig
from finsight.runtime.errors import FinsightError


@pytest.fixture
def tiny_artifact(tmp_path):
    assert importlib.util.find_spec("finsight.chunking.tokenizer"), "Missing pinned tokenizer"
    import tokenizers
    from tokenizers import Tokenizer, models, pre_tokenizers, trainers

    module = importlib.import_module("finsight.chunking.tokenizer")
    root = tmp_path / "tokenizer"
    root.mkdir()
    native = Tokenizer(models.BPE(unk_token="[UNK]"))
    native.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    native.train_from_iterator(
        ["Revenue 2022 €1,000 (25) café\n" * 10],
        trainers.BpeTrainer(
            vocab_size=280,
            special_tokens=["[UNK]"],
            initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),
        ),
    )
    native.save(str(root / "tokenizer.json"))
    for name in ["config.json", "tokenizer_config.json"]:
        (root / name).write_text("{}", encoding="utf-8")
    revision = BaselineConfig().tokenizer_revision
    hashes = {p.name: sha256(p.read_bytes()).hexdigest() for p in root.iterdir()}
    artifact = module.TokenizerArtifact(
        directory=root,
        model="Qwen/Qwen3-Embedding-8B",
        revision=revision,
        sha256s=hashes,
        urls={
            n: f"https://huggingface.co/Qwen/Qwen3-Embedding-8B/resolve/{revision}/{n}"
            for n in hashes
        },
        library_version=tokenizers.__version__,
    )
    return artifact


def test_native_offsets_and_reencoding_preserve_all_source_characters(tiny_artifact, page_factory):
    module = importlib.import_module("finsight.chunking.tokenizer")
    tokenizer = module.LocalOffsetTokenizer(tiny_artifact)
    text = "Revenue 2022 €1,000 (25) café\n" * 70
    assert tokenizer.count(text) != len(text)
    assert all(0 <= a < b <= len(text) for a, b in tokenizer.offsets(text))
    document, page = page_factory(text)
    chunks = importlib.import_module("finsight.chunking.fixed").chunk_pages(
        document, (page,), BaselineConfig(), tokenizer
    )
    covered = set()
    for chunk in chunks:
        span = chunk.source_spans[0]
        assert chunk.content == text[span.char_start : span.char_end]
        assert tokenizer.count(chunk.content) <= 400
        covered.update(range(span.char_start, span.char_end))
    assert covered == set(range(len(text)))


def test_artifact_tamper_rejected_without_download(tiny_artifact):
    module = importlib.import_module("finsight.chunking.tokenizer")
    (tiny_artifact.directory / "config.json").write_text(json.dumps({"tampered": True}))
    with pytest.raises(FinsightError, match="tokenizer_integrity"):
        module.LocalOffsetTokenizer(tiny_artifact)


def test_unavailable_artifact_never_downloads(tmp_path):
    assert importlib.util.find_spec("finsight.chunking.tokenizer"), "Missing pinned tokenizer"
    module = importlib.import_module("finsight.chunking.tokenizer")
    with pytest.raises(FinsightError, match="tokenizer_unavailable"):
        module.TokenizerArtifact.load(tmp_path / "missing")
