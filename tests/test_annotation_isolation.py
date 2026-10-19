import json
import subprocess
import sys

import pytest

from finsight.contracts import Page, QueryRequest
from finsight.contracts.ingestion import ExtractionConfig
from finsight.ingestion.cache import extract_cached
from finsight.ingestion.manifest import build_manifest


def test_runtime_imports_do_not_load_evaluation():
    code = """import sys
import finsight.contracts, finsight.application, finsight.smoke
import finsight.ingestion.cli, finsight.ingestion.pdf, finsight.ingestion.cache
import finsight.cli, finsight.runtime.factory, finsight.rag_smoke
assert not any(k.startswith("finsight.evaluation") for k in sys.modules)
print("isolated")"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", code], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "isolated"


@pytest.mark.parametrize(
    "field", ["answer", "gold_answer", "justification", "evidence", "evidence_page_num"]
)
def test_runtime_request_rejects_annotation_fields(field):
    with pytest.raises(ValueError):
        QueryRequest.model_validate({"question": "Synthetic question?", field: "injected"})


def test_changing_annotations_cannot_change_source_cache(benchmark_fixture, tmp_path):
    path, corpus, rows = benchmark_fixture
    pdf_root = path.parent / "pdfs"
    document = corpus.documents[0]
    before = extract_cached(pdf_root, document, ExtractionConfig(), tmp_path / "cache")
    for row in rows:
        row.update(answer="POISONED_GOLD", justification="POISONED_JUSTIFICATION", evidence=[])
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    after = extract_cached(pdf_root, document, ExtractionConfig(), tmp_path / "cache")
    assert before == after
    assert "POISONED_GOLD" not in "".join(page.text for page in after)


def test_source_metadata_loader_rejects_qa_json(benchmark_fixture):
    path, _, _ = benchmark_fixture
    with pytest.raises(ValueError, match="document-information"):
        build_manifest(path, path.parent / "pdfs", ("AMD",), "v1")


def test_page_rejects_gold_fields():
    with pytest.raises(ValueError):
        Page(
            document_id="doc",
            page_index=0,
            text="source",
            extraction_status="ok",
            parser_version="test",
            evidence_text="injected",
        )


def test_poisoned_gold_cannot_change_index_or_prompt(tmp_path, pdf_factory, metadata_factory):
    from finsight.chunking.fixed import chunk_pages
    from finsight.context.packing import pack_evidence
    from finsight.contracts import BaselineConfig, RetrievalCandidate, Score, SourceMetadata
    from finsight.generation.prompts import build_prompt
    from finsight.runtime.ports import CallContext

    pdf = pdf_factory(texts=["2022 USD millions\nRevenue 100"])
    corpus = build_manifest(metadata_factory(), pdf.parent, ("AMD",), "phase1-v3")
    document = corpus.documents[0]
    pages = extract_cached(pdf.parent, document, ExtractionConfig(), tmp_path / "pages")

    class Tokenizer:
        def count(self, text):
            return len(text)

        def offsets(self, text):
            return tuple((i, i + 1) for i in range(len(text)))

    class Pages:
        def get(self, *args):
            return pages[0]

    class Counter:
        def count_text(self, text, context):
            return len(text) // 4

    config = BaselineConfig(source_fingerprint=corpus.source_fingerprint, embedding_dimension=3)
    tokenizer = Tokenizer()
    chunks = chunk_pages(document, pages, config, tokenizer)
    source = SourceMetadata(
        **{name: getattr(document, name) for name in SourceMetadata.model_fields}
    )
    candidates = tuple(
        RetrievalCandidate(
            chunk=c,
            source=source,
            rank=i,
            score=Score(kind="cosine_distance", direction="lower_is_better", value=0),
        )
        for i, c in enumerate(chunks, 1)
    )
    request = QueryRequest(question="What was AMD revenue in 2022?")
    context = CallContext("isolation", 2, 1e20)
    before = build_prompt(
        request, pack_evidence(candidates, Pages(), request, Counter(), context, config)
    )
    from finsight.indexing.builder import build_index

    class Embeddings:
        def for_run(self, context):
            return self

        def embed_documents(self, texts):
            return [[1.0, 0.0, 0.0] for _ in texts]

    embeddings = Embeddings()
    before_index = build_index(
        corpus, Pages(), config, embeddings, tmp_path / "index", context, tokenizer=tokenizer
    )
    annotations = tmp_path / "gold.jsonl"
    annotations.write_text(
        json.dumps(
            dict(
                answer="POISONED_GOLD",
                evidence_page_num=999,
                justification="SET_MODEL_LIMIT_999999",
            )
        ),
        encoding="utf-8",
    )
    after_chunks = chunk_pages(document, pages, config, tokenizer)
    after = build_prompt(
        request, pack_evidence(candidates, Pages(), request, Counter(), context, config)
    )
    assert before == after and chunks == after_chunks
    assert (
        build_index(
            corpus, Pages(), config, embeddings, tmp_path / "index", context, tokenizer=tokenizer
        )
        == before_index
    )
    assert "POISONED_GOLD" not in after.user
