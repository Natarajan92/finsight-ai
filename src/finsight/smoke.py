"""Synthetic contract exercise. This is not a RAG or provider-backed answer."""

import json

from finsight.contracts import (
    Answer,
    Chunk,
    DocumentManifest,
    Evidence,
    ExperimentConfig,
    Page,
    RetrievalCandidate,
    Score,
    SourceMetadata,
    SourceSpan,
)


def run_smoke() -> dict[str, str | int]:
    source = SourceMetadata(
        doc_name="SYNTHETIC_2022_REPORT",
        company="Synthetic Manufacturing",
        fiscal_period="2022",
        filing_type="synthetic",
        source_url=None,
        local_path="synthetic/report.pdf",
        sha256="a" * 64,
    )
    manifest = DocumentManifest(
        **source.model_dump(),
        document_id="synthetic-document",
        page_count=1,
        ingestion_version="synthetic-v0",
    )
    page = Page(
        document_id=manifest.document_id,
        page_index=0,
        text="2022 | USD millions\nRevenue 1,000\nLoss (25)",
        extraction_status="ok",
        parser_version="synthetic-v0",
    )
    chunk = Chunk(
        chunk_id="synthetic-chunk-0",
        document_id=page.document_id,
        page_start=0,
        page_end=0,
        source_spans=(SourceSpan(page_index=0, char_start=0, char_end=len(page.text)),),
        chunk_strategy="fixed",
        config_fingerprint=ExperimentConfig().fingerprint(),
        content=page.text,
        token_count=12,
        content_type="table",
    )
    candidate = RetrievalCandidate(
        chunk=chunk,
        source=source,
        rank=1,
        score=Score(kind="cosine_similarity", direction="higher_is_better", value=1.0),
    )
    evidence = Evidence(
        chunk_id=candidate.chunk.chunk_id,
        document_id=candidate.chunk.document_id,
        page_index=candidate.chunk.source_spans[0].page_index,
        source_quote=candidate.chunk.content,
        score=candidate.score,
        source=candidate.source,
    )
    answer = Answer(
        status="answered",
        answer_text="Synthetic revenue: 1,000 USD millions.",
        citations=(evidence,),
    )
    restored = Answer.model_validate_json(answer.model_dump_json())
    if restored != answer or restored.citations[0].page_index != 0:
        raise RuntimeError("Synthetic contract roundtrip failed")
    return {
        "check": "synthetic_contract_roundtrip",
        "status": "passed",
        "page_index": restored.citations[0].page_index,
        "cost_usd": "unknown" if restored.usage.cost_usd is None else str(restored.usage.cost_usd),
    }


def main() -> None:
    print(json.dumps(run_smoke(), sort_keys=True))


if __name__ == "__main__":
    main()
