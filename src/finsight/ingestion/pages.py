"""Read existing validated Phase 1 caches; never repair a cache while querying."""

from pathlib import Path

from finsight.contracts import Page
from finsight.contracts.ingestion import CorpusManifest, ExtractionConfig
from finsight.runtime.errors import FinsightError

from .cache import cache_path, load_cached
from .fingerprints import sha256_file
from .manifest import safe_pdf_path


class CachedPageRepository:
    def __init__(
        self,
        corpus: CorpusManifest,
        pdf_root: Path,
        cache_root: Path,
        extraction: ExtractionConfig | None = None,
    ):
        self.documents = {d.document_id: d for d in corpus.documents}
        self.pdf_root = Path(pdf_root)
        self.cache_root = Path(cache_root)
        self.extraction = extraction or ExtractionConfig()
        self._pages = {}
        self._stats = {}

    def _stat(self, document_id: str):
        document = self.documents[document_id]
        pdf = safe_pdf_path(self.pdf_root, document.local_path)
        cache = cache_path(document, self.extraction, self.cache_root)
        return tuple((p.stat().st_size, p.stat().st_mtime_ns) for p in (pdf, cache))

    def validate(self, document_id: str) -> None:
        """Rehash original/cache bytes at reopen and before serving selected evidence."""
        try:
            document = self.documents[document_id]
            pdf = safe_pdf_path(self.pdf_root, document.local_path)
            before = self._stat(document_id)
            if sha256_file(pdf) != document.sha256:
                raise ValueError("Original PDF changed")
            pages = load_cached(document, self.extraction, self.cache_root)
            if before != self._stat(document_id) or sha256_file(pdf) != document.sha256:
                raise ValueError("Source changed during validation")
            self._pages[document_id] = pages
            self._stats[document_id] = before
        except (OSError, ValueError, KeyError):
            raise FinsightError("source_integrity") from None

    def get(self, document_id: str, page_index: int) -> Page:
        try:
            if (
                document_id not in self._pages
                or self._stat(document_id) != self._stats[document_id]
            ):
                self.validate(document_id)
            if not 0 <= page_index < len(self._pages[document_id]):
                raise ValueError("Page outside source")
            return self._pages[document_id][page_index]
        except (OSError, ValueError, KeyError):
            raise FinsightError("source_integrity") from None
