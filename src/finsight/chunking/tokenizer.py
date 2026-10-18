"""Explicit public tokenizer preparation; offline loads verify every pinned asset."""

import json
import re
import tempfile
from hashlib import sha256
from pathlib import Path
from typing import Literal, Self

import httpx
import tokenizers
from pydantic import model_validator
from tokenizers import Tokenizer

from finsight.contracts.base import Contract, NonBlank, Sha256, fingerprint
from finsight.ingestion.cache import write_json_atomic
from finsight.runtime.errors import FinsightError

FILES = {"tokenizer.json", "tokenizer_config.json", "config.json"}
MODEL = "Qwen/Qwen3-Embedding-8B"


class TokenizerArtifact(Contract):
    directory: Path
    model: Literal["Qwen/Qwen3-Embedding-8B"] = MODEL
    revision: NonBlank
    sha256s: dict[str, Sha256]
    urls: dict[str, str]
    library_version: NonBlank
    add_special_tokens: Literal[False] = False

    @model_validator(mode="after")
    def pinned_files(self) -> Self:
        if not re.fullmatch(r"[a-f0-9]{40}", self.revision):
            raise ValueError("Tokenizer revision must identify an immutable commit")
        if set(self.sha256s) != FILES or self.urls != {
            name: f"https://huggingface.co/{MODEL}/resolve/{self.revision}/{name}" for name in FILES
        }:
            raise ValueError("Tokenizer artifact files or URLs differ from the pinned assets")
        return self

    @classmethod
    def load(cls, directory: Path) -> "TokenizerArtifact":
        path = directory / "artifact.json"
        if not path.is_file():
            raise FinsightError("tokenizer_unavailable")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            artifact = cls(directory=directory.resolve(), **payload)
            LocalOffsetTokenizer(artifact)
            return artifact
        except FinsightError:
            raise
        except (OSError, ValueError, TypeError):
            raise FinsightError("tokenizer_integrity") from None

    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json", exclude={"directory"}))


class LocalOffsetTokenizer:
    def __init__(self, artifact: TokenizerArtifact):
        try:
            if artifact.library_version != tokenizers.__version__:
                raise ValueError("Tokenizer library version changed")
            for name, expected in artifact.sha256s.items():
                raw = (artifact.directory / name).read_bytes()
                if sha256(raw).hexdigest() != expected:
                    raise ValueError("Tokenizer bytes changed")
                json.loads(raw)
            self.native = Tokenizer.from_file(str(artifact.directory / "tokenizer.json"))
            self.native.no_truncation()
            self.native.no_padding()
            self.artifact = artifact
        except (OSError, ValueError, Exception) as error:
            # Native tokenizer parsers can raise non-ValueError exceptions.
            raise FinsightError("tokenizer_integrity") from error

    def offsets(self, text: str) -> tuple[tuple[int, int], ...]:
        result = tuple(self.native.encode(text, add_special_tokens=False).offsets)
        if any(not 0 <= start < end <= len(text) for start, end in result):
            raise FinsightError("invalid_source_span")
        return result

    def count(self, text: str) -> int:
        return len(self.native.encode(text, add_special_tokens=False).ids)


def prepare_tokenizer(destination: Path, revision: str) -> TokenizerArtifact:
    """Fetch three public JSON assets only, then atomically publish their manifest."""
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise FinsightError("tokenizer_integrity")
    if destination.exists():
        artifact = TokenizerArtifact.load(destination)
        if artifact.revision != revision:
            raise FinsightError("tokenizer_integrity")
        return artifact
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".tokenizer-staging-", dir=destination.parent))
    urls = {name: f"https://huggingface.co/{MODEL}/resolve/{revision}/{name}" for name in FILES}
    hashes = {}
    try:
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            for name in sorted(FILES):
                with client.stream("GET", urls[name]) as response:
                    response.raise_for_status()
                    count = 0
                    with (stage / name).open("xb") as stream:
                        for part in response.iter_bytes():
                            count += len(part)
                            if count > 100_000_000:
                                raise FinsightError("tokenizer_integrity")
                            stream.write(part)
                hashes[name] = sha256((stage / name).read_bytes()).hexdigest()
        artifact = TokenizerArtifact(
            directory=stage,
            revision=revision,
            sha256s=hashes,
            urls=urls,
            library_version=tokenizers.__version__,
        )
        LocalOffsetTokenizer(artifact)
        write_json_atomic(
            stage / "artifact.json", artifact.model_dump(mode="json", exclude={"directory"})
        )
        stage.rename(destination)
        return TokenizerArtifact.load(destination)
    except FinsightError:
        raise
    except Exception:
        # Leave an incomplete staging directory for diagnosis; it is never a loadable target.
        raise FinsightError("tokenizer_unavailable") from None
