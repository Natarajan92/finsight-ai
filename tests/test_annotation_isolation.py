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
assert not any(k.startswith("finsight.evaluation") for k in sys.modules)
print("isolated")"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", code], capture_output=True, text=True, check=True
    )
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
