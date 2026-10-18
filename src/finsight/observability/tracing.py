"""Atomic per-run local JSONL records; no conflicting overwrite or hosted upload."""

import os
import re
import tempfile
from pathlib import Path

from finsight.contracts.tracing import RunTrace
from finsight.runtime.errors import FinsightError


class JsonlTraceRecorder:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _path(self, run_id: str) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", run_id):
            raise FinsightError("trace_integrity")
        return self.root / (run_id + ".jsonl")

    def load(self, run_id: str) -> RunTrace:
        try:
            trace = RunTrace.model_validate_json(self._path(run_id).read_text(encoding="utf-8"))
            if trace.run_id != run_id:
                raise ValueError("Trace identity changed")
            return trace
        except (OSError, ValueError):
            raise FinsightError("trace_integrity") from None

    def record(self, trace: RunTrace) -> None:
        destination = self._path(trace.run_id)
        self.root.mkdir(parents=True, exist_ok=True)
        payload = (trace.model_dump_json() + "\n").encode("utf-8")
        descriptor, temporary = tempfile.mkstemp(dir=self.root, suffix=".tmp")
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, destination)
            except FileExistsError:
                if destination.read_bytes() != payload:
                    raise FinsightError("trace_conflict") from None
        except FinsightError:
            raise
        except OSError:
            raise FinsightError("trace_write_failed") from None
        finally:
            try:
                Path(temporary).unlink(missing_ok=True)
            except OSError:
                pass  # The terminal file is already durable; do not repeat a model call.
