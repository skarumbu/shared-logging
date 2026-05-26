import json
import logging
import functools
import time
from datetime import datetime, timezone


class _JSONFormatter(logging.Formatter):
    """Formats log records as structured JSON matching the shared-logging schema."""

    _SCHEMA_FIELDS = ("endpoint", "method", "status", "duration_ms",
                      "error_type", "stack_trace")

    def format(self, record: logging.LogRecord) -> str:
        now = datetime.now(timezone.utc)
        timestamp = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"

        entry: dict = {
            "event": getattr(record, "event", "log"),
            "service": record.name,
            "timestamp": timestamp,
        }

        for field in self._SCHEMA_FIELDS:
            val = getattr(record, field, None)
            if val is not None:
                entry[field] = val

        # Handle 'message' extra field stored as _message_extra to avoid LogRecord conflict
        message_extra = getattr(record, "_message_extra", None)
        if message_extra is not None:
            entry["message"] = message_extra
        else:
            # Include the log message string only when non-empty
            msg = record.getMessage()
            if msg:
                entry["message"] = msg

        return json.dumps(entry, default=str)


class _Logger(logging.Logger):
    """Logger that safely handles 'message' in extra without raising KeyError."""

    def makeRecord(self, name, level, fn, lno, msg, args, exc_info,
                   func=None, extra=None, sinfo=None):
        # Python's logging raises KeyError if 'message' is in extra (reserved attribute).
        # Extract it and re-attach under a safe name for the formatter to consume.
        message_extra = None
        if extra and "message" in extra:
            extra = dict(extra)
            message_extra = extra.pop("message")

        record = super().makeRecord(name, level, fn, lno, msg, args, exc_info,
                                    func=func, extra=extra, sinfo=sinfo)
        if message_extra is not None:
            record._message_extra = message_extra
        return record


def get_logger(service_name: str) -> logging.Logger:
    """Return a structured JSON logger for the given service name.

    Idempotent: calling multiple times with the same name returns the same logger
    without adding duplicate handlers.
    """
    logger = logging.getLogger(service_name)
    # Upgrade to _Logger if needed so 'message' in extra is handled safely
    if not isinstance(logger, _Logger):
        logger.__class__ = _Logger
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(_JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def log_request(logger: logging.Logger):
    """Decorator for Azure Functions HTTP triggers. Logs every request and re-raises exceptions."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(req, *args, **kwargs):
            start = time.monotonic()
            # Extract endpoint from URL path after /api
            try:
                path = str(req.url).split("?")[0]
                endpoint = "/" + path.split("/api", 1)[-1].lstrip("/") if "/api" in path else path
            except Exception:
                endpoint = "unknown"
            method = getattr(req, "method", "UNKNOWN")
            try:
                response = func(req, *args, **kwargs)
                status = getattr(response, "status_code", 200)
                duration_ms = round((time.monotonic() - start) * 1000, 1)
                logger.info("", extra={
                    "event": "error" if status >= 400 else "request",
                    "endpoint": endpoint,
                    "method": method,
                    "status": status,
                    "duration_ms": duration_ms,
                })
                return response
            except Exception as exc:
                import traceback as _tb
                duration_ms = round((time.monotonic() - start) * 1000, 1)
                logger.error("", extra={
                    "event": "error",
                    "endpoint": endpoint,
                    "method": method,
                    "status": 500,
                    "message": str(exc),
                    "error_type": type(exc).__name__,
                    "stack_trace": _tb.format_exc()[:2000],
                    "duration_ms": duration_ms,
                })
                raise
        return wrapper
    return decorator
