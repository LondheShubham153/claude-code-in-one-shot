import logging
import sys

from pythonjsonlogger.json import JsonFormatter

_REDACT_KEYS = {"safe_browsing_api_key", "ngrok_authtoken", "postgres_password"}


class _RedactingFormatter(JsonFormatter):
    def add_fields(
        self,
        log_record: dict,  # type: ignore[type-arg]
        record: logging.LogRecord,
        message_dict: dict,  # type: ignore[type-arg]
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        for k in list(log_record.keys()):
            if k.lower() in _REDACT_KEYS:
                log_record[k] = "***REDACTED***"


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_RedactingFormatter("%(levelname)s %(name)s %(message)s"))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    # Quiet down some chatty libs
    for noisy in ("httpx", "httpcore", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
