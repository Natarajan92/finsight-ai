"""Synthetic fixtures only. Unit tests must never connect to a service."""

import socket

import pytest


@pytest.fixture(autouse=True)
def block_network(request, monkeypatch):
    if request.node.get_closest_marker("integration"):
        return

    def denied(*args, **kwargs):
        raise AssertionError("Network access is forbidden in unit tests")

    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)


@pytest.fixture
def source():
    return {
        "doc_name": "SYNTHETIC_2022_REPORT",
        "company": "Synthetic Manufacturing",
        "fiscal_period": "2022",
        "filing_type": "synthetic",
        "source_url": None,
        "local_path": "synthetic/report.pdf",
        "sha256": "a" * 64,
    }


@pytest.fixture
def chunk_data():
    return {
        "chunk_id": "synthetic-chunk-0",
        "document_id": "synthetic-document",
        "page_start": 0,
        "page_end": 0,
        "source_spans": [{"page_index": 0, "char_start": 0, "char_end": 40}],
        "chunk_strategy": "fixed",
        "config_fingerprint": "b" * 64,
        "content": "2022 | USD millions\nRevenue 1,000\nLoss (25)",
        "token_count": 12,
    }


@pytest.fixture
def score():
    return {"kind": "cosine_similarity", "direction": "higher_is_better", "value": 0.75}


@pytest.fixture
def evidence_data(source, score):
    return {
        "chunk_id": "synthetic-chunk-0",
        "document_id": "synthetic-document",
        "page_index": 0,
        "source_quote": "Revenue 1,000",
        "source": source,
        "score": score,
    }
