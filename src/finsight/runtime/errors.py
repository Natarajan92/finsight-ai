"""Safe failure messages crossing application boundaries."""


class FinsightError(Exception):
    def __init__(self, code: str, message: str = "", retryable: bool = False):
        self.code = code
        self.message = message or code
        self.retryable = retryable
        super().__init__(f"{code}: {self.message}")
