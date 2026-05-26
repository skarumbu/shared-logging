import json
import logging
from datetime import datetime, timezone


def _build_json(record: logging.LogRecord, message_override=None) -> str:
    """Build the structured JSON string from a LogRecord."""
    entry: dict = {
        "event": getattr(record, "event", "log"),
        "service": record.name,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") +
                     f"{datetime.now(timezone.utc).microsecond // 1000:03d}Z",
    }
    for field in ("endpoint", "method", "status", "duration_ms",
                  "error_type", "stack_trace"):
        val = getattr(record, field, None)
        if val is not None:
            entry[field] = val
    # message: prefer explicit extra field, fall back to non-empty log message
    if message_override is not None:
        entry["message"] = message_override
    else:
        msg = record.getMessage()
        if msg:
            entry["message"] = msg
    return json.dumps(entry)


class _JSONFormatter(logging.Formatter):
    """Formatter that emits structured JSON. Used when handler has no formatter."""

    def format(self, record: logging.LogRecord) -> str:
        message_override = getattr(record, "_message_override", None)
        return _build_json(record, message_override)


class _Logger(logging.Logger):
    """Logger subclass that:
    - Allows 'message' in extra kwargs without raising KeyError.
    - Pre-bakes JSON into record.msg so any handler (even unformatted) outputs JSON.
    """

    def makeRecord(self, name, level, fn, lno, msg, args, exc_info,
                   func=None, extra=None, sinfo=None):
        # Pull 'message' out of extra before the parent's makeRecord rejects it.
        message_override = None
        if extra and "message" in extra:
            extra = dict(extra)
            message_override = extra.pop("message")

        record = super().makeRecord(name, level, fn, lno, msg, args, exc_info,
                                    func=func, extra=extra, sinfo=sinfo)

        # Store override for formatter use
        if message_override is not None:
            record._message_override = message_override

        # Pre-bake the JSON into record.msg so any plain StreamHandler outputs it.
        # Clear args so getMessage() returns the JSON string as-is.
        record.msg = _build_json(record, message_override)
        record.args = ()

        return record


def get_logger(service_name: str) -> logging.Logger:
    # Ensure the logger is an instance of _Logger so makeRecord override applies.
    original_class = logging.getLoggerClass()
    logging.setLoggerClass(_Logger)
    logger = logging.getLogger(service_name)
    logging.setLoggerClass(original_class)

    # Upgrade an already-existing plain Logger instance to _Logger in-place
    if not isinstance(logger, _Logger):
        logger.__class__ = _Logger

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(_JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger
