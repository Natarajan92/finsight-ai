"""The local scorer must rerank the full pool without dropping long-passage tails."""

import importlib
from types import SimpleNamespace

import pytest
from tokenizers import Tokenizer, models, pre_tokenizers, processors

from finsight.contracts import Chunk, RetrievalCandidate
from finsight.contracts.retrieval_experiments import RerankerConfig
from finsight.runtime.errors import FinsightError
from finsight.runtime.ports import CallContext


def reranking_module():
    assert importlib.util.find_spec("finsight.retrieval.reranking"), "Missing local reranker"
    return importlib.import_module("finsight.retrieval.reranking")


@pytest.fixture
def pool(source, score):
    return tuple(
        RetrievalCandidate(
            chunk=Chunk(
                chunk_id=f"{i:064x}",
                document_id="synthetic",
                page_start=0,
                page_end=0,
                source_spans=[dict(page_index=0, char_start=0, char_end=20)],
                chunk_strategy="fixed",
                config_fingerprint="a" * 64,
                content=f"financial passage {i}",
                token_count=4,
            ),
            source=source,
            rank=i,
            score=score,
        )
        for i in range(1, 16)
    )


def tiny_tokenizer():
    tokenizer = Tokenizer(
        models.WordLevel(
            {
                "[PAD]": 0,
                "[UNK]": 1,
                "[CLS]": 2,
                "[SEP]": 3,
                "financial": 4,
                "passage": 5,
                "tail": 6,
            },
            unk_token="[UNK]",
        )
    )
    tokenizer.pre_tokenizer = pre_tokenizers.Whitespace()
    tokenizer.post_processor = processors.TemplateProcessing(
        single="[CLS] $A [SEP]",
        pair="[CLS] $A [SEP] $B:1 [SEP]:1",
        special_tokens=[("[CLS]", 2), ("[SEP]", 3)],
    )
    return tokenizer


def test_last_candidate_can_become_first_without_losing_dense_provenance(pool, tmp_path):
    module = reranking_module()

    class Backend:
        tokenizer = tiny_tokenizer()

        def fingerprint(self):
            return "b" * 64

        def score(self, encodings, context):
            return [float(i) for i in range(self.offset, self.offset + len(encodings))]

        offset = 0

    backend = Backend()

    def score(encodings, context):
        result = list(range(backend.offset, backend.offset + len(encodings)))
        backend.offset += len(encodings)
        return result

    backend.score = score
    reranker = module.LocalReranker(backend, RerankerConfig(), tmp_path)
    result = reranker.rerank("revenue?", pool, CallContext("r", 3, 1e20))
    assert result.candidates[0].chunk.chunk_id == pool[-1].chunk.chunk_id
    assert result.candidates[0].chunk == pool[-1].chunk
    assert result.details[0].original_rank == 15
    assert result.details[0].dense_score == pool[-1].score
    assert result.candidates[0].score.kind == "rerank_logit"
    assert len(result.candidates) == 15
    backend.score = lambda *args: (_ for _ in ()).throw(
        AssertionError("cache must avoid inference")
    )
    replay = reranker.rerank("revenue?", pool, CallContext("r2", 3, 1e20))
    assert replay.candidates == result.candidates and replay.cache_hit


def test_overflow_windows_cover_tail_and_ties_use_chunk_id(pool):
    module = reranking_module()
    text = "financial " * 1200 + "tail"
    candidate = pool[0].model_copy(
        update={
            "chunk": pool[0].chunk.model_copy(
                update={
                    "content": text,
                    "source_spans": (
                        pool[0].chunk.source_spans[0].model_copy(update={"char_end": len(text)}),
                    ),
                }
            )
        }
    )
    backend = SimpleNamespace(
        tokenizer=tiny_tokenizer(),
        fingerprint=lambda: "c" * 64,
        score=lambda encodings, ctx: [9.0 if 6 in e.ids else 0.0 for e in encodings],
    )
    reranker = module.LocalReranker(backend, RerankerConfig())
    result = reranker.rerank("question", (candidate,), CallContext("r", 3, 1e20))
    windows = result.details[0].windows
    assert len(windows) >= 3 and max(w.token_end for w in windows) == 1201
    covered = {i for w in windows for i in range(w.token_start, w.token_end)}
    assert covered == set(range(1201))
    assert windows[-1].char_end == len(text)
    assert result.details[0].rerank_score.value == 9.0
    ties = reranker.rerank("question", tuple(reversed(pool)), CallContext("ties", 3, 1e20))
    assert [c.chunk.chunk_id for c in ties.candidates] == sorted(c.chunk.chunk_id for c in pool)


def test_long_query_nonfinite_logits_and_scorer_failures_are_explicit(pool):
    module = reranking_module()
    backend = SimpleNamespace(
        tokenizer=tiny_tokenizer(),
        fingerprint=lambda: "d" * 64,
        score=lambda encodings, ctx: [float("nan")] * len(encodings),
    )
    reranker = module.LocalReranker(backend, RerankerConfig())
    with pytest.raises(FinsightError, match="rerank_query_limit"):
        reranker.rerank("question " * 510, pool, CallContext("q", 3, 1e20))
    with pytest.raises(FinsightError, match="rerank_output"):
        reranker.rerank("question", pool, CallContext("n", 3, 1e20))
    backend.score = lambda *args: (_ for _ in ()).throw(RuntimeError("private backend error"))
    with pytest.raises(FinsightError, match="rerank_failed"):
        reranker.rerank("question", pool, CallContext("f", 3, 1e20))


def test_missing_or_changed_model_artifact_fails_offline(tmp_path):
    module = reranking_module()
    with pytest.raises(FinsightError, match="reranker_unavailable"):
        module.OnnxCrossEncoder(tmp_path, RerankerConfig())
    import json

    (tmp_path / "artifact.json").write_text(
        json.dumps(
            dict(
                model=RerankerConfig().model,
                revision=RerankerConfig().revision,
                sha256s={"onnx/model.onnx": "a" * 64},
            )
        )
    )
    with pytest.raises(FinsightError, match="reranker_integrity"):
        module.OnnxCrossEncoder(tmp_path, RerankerConfig())


def test_public_download_rejects_wrong_weights_without_publishing(tmp_path):
    import httpx

    from finsight.retrieval.reranker_artifacts import prepare_reranker

    def respond(request):
        name = request.url.path.rsplit("/", 1)[-1]
        if name == "tokenizer.json":
            return httpx.Response(200, text=tiny_tokenizer().to_str())
        if name == "tokenizer_config.json":
            return httpx.Response(200, json={"model_max_length": 512})
        return httpx.Response(200, content=b"unapproved weights")

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(FinsightError, match="reranker_integrity"):
            prepare_reranker(tmp_path / "model", client=client)
    assert not (tmp_path / "model").exists()
    assert not list(tmp_path.glob("reranker-*"))
