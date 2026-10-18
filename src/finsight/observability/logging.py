"""Redact configured credentials after rendering messages and exception traces."""

import logging
import sys
from typing import TextIO

from finsight.config import Settings


class _RedactingFormatter(logging.Formatter):
    def __init__(self, secrets: tuple[str, ...]):
        super().__init__("%(levelname)s %(name)s %(message)s")
        self._secrets = secrets

    def format(self, record: logging.LogRecord) -> str:
        rendered = super().format(record)
        for secret in self._secrets:
            rendered = rendered.replace(secret, "[REDACTED]")
        return rendered


class _SafeStreamHandler(logging.StreamHandler):
    def handleError(self, record: logging.LogRecord) -> None:
        # The default handler prints raw msg/args and tracebacks on failure.
        # Never render the failed record or exception a second time.
        try:
            sys.stderr.write("FinSight logging output failed; event suppressed.\n")
        except Exception:
            pass  # Logging failures must not interrupt application error handling.


def configure_logging(settings: Settings, *, stream: TextIO | None = None) -> logging.Logger:
    """Own only the finsight logger; do not forward unredacted records to root."""
    secrets = tuple(
        value.get_secret_value()
        for value in (settings.api_key, settings.nebius_api_key, settings.anthropic_api_key)
        if value and value.get_secret_value()
    )
    handler = _SafeStreamHandler(stream)
    handler.setFormatter(_RedactingFormatter(secrets))
    logger = logging.getLogger("finsight")
    for previous in logger.handlers[:]:
        logger.removeHandler(previous)
        previous.close()
    logger.addHandler(handler)
    logger.setLevel(settings.log_level)
    logger.propagate = False
    return logger
