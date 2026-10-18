import json

import pytest

from finsight.ingestion.cli import main


def test_synthetic_manifest_extract_cli(pdf_factory, metadata_factory, tmp_path, capsys):
    path = pdf_factory()
    manifest = tmp_path / "manifest.json"
    assert (
        main(
            [
                "manifest",
                "--metadata",
                str(metadata_factory()),
                "--pdf-root",
                str(path.parent),
                "--output",
                str(manifest),
                "--companies",
                "AMD",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["documents"] == 1
    assert (
        main(
            [
                "extract",
                "--manifest",
                str(manifest),
                "--pdf-root",
                str(path.parent),
                "--cache-root",
                str(tmp_path / "cache"),
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["pages"] == 2 and result["ok"] == 1 and result["empty"] == 1
    assert result["error"] == 0


def test_ingestion_cli_rejects_annotations():
    with pytest.raises(SystemExit) as exc:
        main(
            [
                "extract",
                "--manifest",
                "source.json",
                "--pdf-root",
                ".",
                "--cache-root",
                "cache",
                "--gold-answer",
                "must-never-enter-runtime",
            ]
        )
    assert exc.value.code == 2
