"""Offline source browsing and explicitly guarded answers for one AMD filing."""

from finsight.config import Settings
from finsight.contracts import QueryRequest
from finsight.runtime.errors import FinsightError
from finsight.runtime.experiment_factory import create_experiment_lab
from finsight.runtime.experiment_pilot import scoped_request


class AmdWorkspace:
    def __init__(self, lab):
        scoped_request(lab, QueryRequest(question="Scope check"), "A")
        self.lab = lab
        self.document = lab.corpus.documents[0]
        self.chunk_count = lab.open("A").manifest.chunk_count

    def page(self, number: int):
        if type(number) is not int or not 1 <= number <= self.document.page_count:
            raise FinsightError("page_unavailable")
        self.lab.pages.validate(self.document.document_id)
        return self.lab.pages.get(self.document.document_id, number - 1)

    def ask(self, question: str, *, allow_paid: bool = False):
        return self.lab.ask_pilot(
            QueryRequest(question=question.strip()), "A", allow_paid=allow_paid
        )

    def close(self):
        self.lab.close()


def open_workspace(settings: Settings | None = None) -> AmdWorkspace:
    lab = create_experiment_lab(settings or Settings(), doc_name="AMD_2022_10K")
    try:
        return AmdWorkspace(lab)
    except Exception:
        lab.close()
        raise
