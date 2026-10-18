"""Synthetic fixtures only. Unit tests must never connect to a service."""

import json
import socket

import pytest


@pytest.fixture
def pdf_factory(tmp_path):
    import pymupdf

    root = tmp_path / "pdfs"
    root.mkdir()

    def create(name="AMD_2022_10K", texts=None, password=None):
        path = root / f"{name}.pdf"
        with pymupdf.open() as document:
            for text in (
                texts
                if texts is not None
                else [
                    "Financial statements 2022 2021\nUSD millions\n"
                    "Revenue 1,000 900\nLoss (25) -10\nNote 1: café",
                    "",
                ]
            ):
                page = document.new_page()
                if text:
                    page.insert_text((50, 70), text)
            options = (
                {}
                if password is None
                else {
                    "encryption": pymupdf.PDF_ENCRYPT_AES_256,
                    "owner_pw": password,
                    "user_pw": password,
                }
            )
            document.save(path, **options)
        return path

    return create


@pytest.fixture
def metadata_factory(tmp_path):
    def create(records=None):
        path = tmp_path / "metadata.jsonl"
        if records is None:
            records = [
                {
                    "doc_name": "AMD_2022_10K",
                    "company": "AMD",
                    "gics_sector": None,
                    "doc_type": "10K",
                    "doc_period": 2022,
                    "doc_link": None,
                }
            ]
        path.write_text("".join(json.dumps(row) + "\n" for row in records), encoding="utf-8")
        return path

    return create


@pytest.fixture
def benchmark_fixture(pdf_factory, metadata_factory, tmp_path):
    """Synthetic questions/gold; only public reasoning-count patterns are reproduced."""
    from finsight.ingestion.manifest import build_manifest

    patterns = {
        "AMD": {"numeric": 2, "logical_or_logical": 1, "extract": 2, "combined": 1, None: 2},
        "American Express": {
            "extract": 2,
            "numeric_or_extract": 1,
            "combined": 1,
            "numeric": 1,
            None: 2,
        },
        "PepsiCo": {"extract": 4, "numeric": 2, None: 5},
        "Boeing": {
            "extract": 2,
            "logical": 1,
            "numeric_or_extract": 1,
            "extract_or_logical": 1,
            None: 3,
        },
        "Amcor": {
            "extract": 2,
            None: 4,
            "numeric_or_logical": 1,
            "malformed_or": 1,
            "numeric_or_extract": 1,
        },
        "Johnson & Johnson": {"logical": 1, "combined": 1, "numeric_or_logical": 1, None: 6},
    }
    metadata, cases = [], []
    root = None
    for index, (company, labels) in enumerate(patterns.items()):
        path = pdf_factory(name=f"SYNTHETIC_{index}")
        root = path.parent
        metadata.append(
            {
                "doc_name": path.stem,
                "company": company,
                "gics_sector": None,
                "doc_type": "AnnualReport",
                "doc_period": 2022,
                "doc_link": None,
            }
        )
        for label, count in labels.items():
            for _ in range(count):
                identity = f"synthetic-{len(cases):03d}"
                cases.append(
                    {
                        "financebench_id": identity,
                        "company": company,
                        "doc_name": path.stem,
                        "question_type": "synthetic",
                        "question_reasoning": label,
                        "domain_question_num": None,
                        "question": f"Synthetic question {identity}?",
                        "answer": f"GOLD_ONLY_{identity}",
                        "justification": None,
                        "dataset_subset_label": "synthetic",
                        "evidence": [
                            {
                                "doc_name": path.stem,
                                "evidence_page_num": 0,
                                "evidence_text": "Revenue 1,000",
                                "evidence_text_full_page": "GOLD_PAGE_ONLY",
                            }
                        ],
                    }
                )
    corpus = build_manifest(metadata_factory(metadata), root, tuple(patterns), "v1")
    questions = tmp_path / "questions.jsonl"
    questions.write_text("".join(json.dumps(case) + "\n" for case in cases), encoding="utf-8")
    return questions, corpus, cases


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
