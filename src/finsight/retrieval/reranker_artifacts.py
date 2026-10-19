"""Explicit pinned public downloads and offline CPU ONNX inference."""

import json
import os
import shutil
import tempfile
from importlib.metadata import version
from pathlib import Path
from typing import Literal

import httpx
from tokenizers import Tokenizer

from finsight.contracts.base import Contract, Sha256, fingerprint
from finsight.contracts.retrieval_experiments import RerankerConfig
from finsight.ingestion.cache import write_json_atomic
from finsight.ingestion.fingerprints import sha256_file
from finsight.runtime.deadlines import bounded_call
from finsight.runtime.errors import FinsightError

ASSETS = ("onnx/model.onnx", "tokenizer.json", "tokenizer_config.json", "config.json")


class RerankerArtifact(Contract):
    schema_version: Literal["1"] = "1"
    model: Literal["cross-encoder/ms-marco-MiniLM-L6-v2"]
    revision: Literal["eeed17e3bfc6fa06a790f2d12a9501fec587fccf"]
    sha256s: dict[str, Sha256]

    def fingerprint(self):
        return fingerprint(self.model_dump(mode="json"))

    @classmethod
    def load(cls, directory: Path):
        path = Path(directory) / "artifact.json"
        if not path.is_file():
            raise FinsightError("reranker_unavailable")
        try:
            artifact = cls.model_validate_json(path.read_text(encoding="utf-8"))
            expected = RerankerConfig()
            if set(artifact.sha256s) != set(ASSETS):
                raise ValueError("Wrong artifact files")
            if artifact.sha256s[expected.model_file] != expected.model_sha256:
                raise ValueError("Unapproved model weights")
            for name, digest in artifact.sha256s.items():
                if sha256_file(Path(directory) / name) != digest:
                    raise ValueError("Artifact changed")
            if (
                json.loads((Path(directory) / "tokenizer_config.json").read_text())[
                    "model_max_length"
                ]
                != 512
            ):
                raise ValueError("Unexpected pair limit")
            Tokenizer.from_file(str(Path(directory) / "tokenizer.json"))
            return artifact
        except (ValueError, OSError, KeyError, TypeError):
            raise FinsightError("reranker_integrity") from None


def prepare_reranker(destination: Path, *, client: httpx.Client | None = None):
    """Public assets only. Nothing calls this from an import or offline loader."""
    destination = Path(destination)
    if destination.exists():
        return RerankerArtifact.load(destination)
    config = RerankerConfig()
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="reranker-", dir=destination.parent))
    owned = client is None
    client = client or httpx.Client(
        transport=httpx.HTTPTransport(retries=0), timeout=20, follow_redirects=True
    )
    try:
        hashes = {}
        for name in ASSETS:
            path = stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            url = f"https://huggingface.co/{config.model}/resolve/{config.revision}/{name}"
            size = 0
            with client.stream("GET", url, follow_redirects=True) as response:
                response.raise_for_status()
                with path.open("wb") as handle:
                    for part in response.iter_bytes():
                        size += len(part)
                        if size > 128 * 1024 * 1024:
                            raise FinsightError("reranker_download_limit")
                        handle.write(part)
            hashes[name] = sha256_file(path)
        artifact = RerankerArtifact(model=config.model, revision=config.revision, sha256s=hashes)
        write_json_atomic(stage / "artifact.json", artifact.model_dump(mode="json"))
        RerankerArtifact.load(stage)
        os.replace(stage, destination)
        return artifact
    except FinsightError:
        raise
    except Exception:
        raise FinsightError("reranker_download_failed") from None
    finally:
        if owned:
            client.close()
        # Only this function's freshly-created staging directory is removed.
        if stage.exists():
            if stage.resolve().parent != destination.parent.resolve() or not stage.name.startswith(
                "reranker-"
            ):
                raise FinsightError("reranker_integrity")
            shutil.rmtree(stage)


class OnnxCrossEncoder:
    def __init__(self, directory: Path, config: RerankerConfig):
        artifact = RerankerArtifact.load(directory)
        try:
            import onnxruntime as ort

            options = ort.SessionOptions()
            options.intra_op_num_threads = config.threads
            options.inter_op_num_threads = 1
            self.session = ort.InferenceSession(
                str(Path(directory) / config.model_file),
                sess_options=options,
                providers=[config.provider],
            )
            if set(i.name for i in self.session.get_inputs()) != {
                "input_ids",
                "attention_mask",
                "token_type_ids",
            }:
                raise ValueError("Unexpected ONNX inputs")
            self.tokenizer = Tokenizer.from_file(str(Path(directory) / "tokenizer.json"))
            self.tokenizer.no_padding()
            self.tokenizer.no_truncation()
            self.identity = fingerprint(
                dict(
                    artifact=artifact.fingerprint(),
                    onnxruntime=version("onnxruntime"),
                    numpy=version("numpy"),
                    provider=config.provider,
                )
            )
        except Exception:
            raise FinsightError("reranker_integrity") from None

    def fingerprint(self):
        return self.identity

    def score(self, encodings, context):
        import numpy as np

        context.remaining()
        maximum = max(len(e.ids) for e in encodings)
        inputs = {
            name: np.asarray(
                [getattr(e, attr) + [0] * (maximum - len(e.ids)) for e in encodings], dtype=np.int64
            )
            for name, attr in (
                ("input_ids", "ids"),
                ("attention_mask", "attention_mask"),
                ("token_type_ids", "type_ids"),
            )
        }
        result = bounded_call(lambda: self.session.run(None, inputs)[0], context.remaining())
        context.remaining()
        values = np.asarray(result)
        if values.shape != (len(encodings), 1):
            raise FinsightError("rerank_output")
        return values[:, 0].tolist()
