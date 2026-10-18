"""Synthetic source -> Chroma -> service -> cited Answer, without remote providers."""

import json
import tempfile
from pathlib import Path
from time import monotonic
from uuid import uuid4

from finsight.application import BaselineApplicationService
from finsight.contracts import BaselineConfig, QueryRequest
from finsight.contracts.generation import DraftAnswer
from finsight.contracts.ingestion import ExtractionConfig
from finsight.indexing.builder import build_index, open_index
from finsight.ingestion.cache import extract_cached
from finsight.ingestion.manifest import build_manifest
from finsight.ingestion.pages import CachedPageRepository
from finsight.observability.tracing import JsonlTraceRecorder
from finsight.runtime.ports import CallContext


class _SyntheticTokenizer:
    def count(self, text):
        return len(text)

    def offsets(self, text):
        return tuple((i, i + 1) for i in range(len(text)))


class _SyntheticEmbeddings:
    def for_run(self, context):
        return self

    def embed_documents(self, texts):
        return [[1.0, 0.0, 0.0] for _ in texts]

    def embed_query(self, text):
        return [1.0, 0.0, 0.0]


class _SyntheticCounter:
    def count_text(self, text, context):
        context.remaining()
        return max(1, len(text) // 4)

    def count_prompt(self, *args):
        return 1000


class _SyntheticGenerator:
    def generate(self, prompt, context):
        payload = json.loads(prompt.user)
        item = next(s for s in payload["sources"]["evidence"] if "Revenue 1,000" in s["text"])
        return DraftAnswer(
            status="answered",
            claims=[
                dict(
                    text="AMD revenue was 1,000 USD millions in 2022.",
                    references=[dict(evidence_id=item["evidence_id"], quote="Revenue 1,000")],
                )
            ],
        )


def run_rag_smoke() -> dict[str, object]:
    import pymupdf

    with tempfile.TemporaryDirectory(prefix="finsight-rag-") as temporary:
        root = Path(temporary)
        pdf_root = root / "pdfs"
        pdf_root.mkdir()
        with pymupdf.open() as pdf:
            page = pdf.new_page()
            page.insert_text((50, 70), "2022 USD millions\nRevenue 1,000\nLoss (25)")
            pdf.save(pdf_root / "Synthetic_2022_10K.pdf")
        metadata = root / "metadata.jsonl"
        metadata.write_text(
            json.dumps(
                dict(
                    doc_name="Synthetic_2022_10K",
                    company="AMD",
                    gics_sector=None,
                    doc_type="10K",
                    doc_period=2022,
                    doc_link=None,
                )
            )
            + "\n",
            encoding="utf-8",
        )
        corpus = build_manifest(metadata, pdf_root, ("AMD",), "phase1-v3")
        for document in corpus.documents:
            extract_cached(pdf_root, document, ExtractionConfig(), root / "pages")
        pages = CachedPageRepository(corpus, pdf_root, root / "pages")
        config = BaselineConfig(source_fingerprint=corpus.source_fingerprint, embedding_dimension=3)
        tokenizer = _SyntheticTokenizer()
        embeddings = _SyntheticEmbeddings()
        manifest = build_index(
            corpus,
            pages,
            config,
            embeddings,
            root / "index",
            CallContext(uuid4().hex, 2, monotonic() + 45),
            tokenizer=tokenizer,
        )
        retriever = open_index(
            root / "index", config, corpus, pages=pages, embeddings=embeddings, tokenizer=tokenizer
        )
        sink = JsonlTraceRecorder(root / "traces")
        service = BaselineApplicationService(
            config, retriever, _SyntheticCounter(), _SyntheticGenerator(), pages, sink
        )
        try:
            answer = service.answer(QueryRequest(question="What was AMD revenue in 2022?"))
            if answer.status != "answered" or sink.load(service.last_trace_id).answer != answer:
                raise ValueError("Synthetic RAG roundtrip failed")
            return dict(
                check="synthetic_rag_roundtrip",
                status="passed",
                answer_status=answer.status,
                page_index=answer.citations[0].page_index,
                indexed_chunks=manifest.chunk_count,
                provider_network_calls=0,
                cost_usd="unknown",
            )
        finally:
            retriever.store.client.close()
