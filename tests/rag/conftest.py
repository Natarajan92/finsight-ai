"""Small source-only builders; providers and tokenizers are deterministic fakes."""

import pytest

from finsight.contracts import DocumentManifest, Page


class CharacterTokenizer:
    def count(self, text):
        return len(text)

    def offsets(self, text):
        return tuple((i, i + 1) for i in range(len(text)))


@pytest.fixture
def char_tokenizer():
    return CharacterTokenizer()


@pytest.fixture
def page_factory(source):
    document = DocumentManifest(
        **source, document_id="synthetic-document", page_count=1, ingestion_version="synthetic-v1"
    )

    def make(text="Revenue 2022 | USD millions\nRevenue 1,000\nLoss (25)", **changes):
        data = dict(
            document_id=document.document_id,
            page_index=0,
            text=text,
            extraction_status="ok",
            parser_version="synthetic-v1",
        )
        data.update(changes)
        return document, Page(**data)

    return make
