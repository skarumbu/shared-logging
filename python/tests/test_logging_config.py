import json
import logging
import sys
import io
import pytest

sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))
from shared_logging import get_logger


def _capture_log(fn):
    """Call fn(logger) and return the parsed JSON line written to stdout."""
    logger = get_logger("test-svc")
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    # Replace existing handlers to capture output
    logger.handlers = [handler]
    fn(logger)
    output = buf.getvalue().strip()
    return json.loads(output)


def test_get_logger_returns_logger():
    logger = get_logger("test-svc")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test-svc"


def test_request_log_has_required_fields():
    data = _capture_log(lambda log: log.info(
        "", extra={"event": "request", "endpoint": "/test", "method": "GET",
                   "status": 200, "duration_ms": 50.0}
    ))
    assert data["event"] == "request"
    assert data["service"] == "test-svc"
    assert data["endpoint"] == "/test"
    assert data["method"] == "GET"
    assert data["status"] == 200
    assert data["duration_ms"] == 50.0
    assert "timestamp" in data
    # No empty message field on request logs
    assert "message" not in data


def test_error_log_has_required_fields():
    data = _capture_log(lambda log: log.error(
        "", extra={"event": "error", "endpoint": "/test", "method": "POST",
                   "status": 500, "message": "boom", "error_type": "ValueError",
                   "stack_trace": "line 1\nline 2", "duration_ms": 12.3}
    ))
    assert data["event"] == "error"
    assert data["service"] == "test-svc"
    assert data["error_type"] == "ValueError"
    assert data["stack_trace"] == "line 1\nline 2"
    assert data["message"] == "boom"


def test_none_fields_are_omitted():
    data = _capture_log(lambda log: log.info(
        "", extra={"event": "request", "endpoint": "/test", "method": "GET",
                   "status": 200, "duration_ms": 10.0}
    ))
    # Fields not provided should not appear
    assert "stack_trace" not in data
    assert "error_type" not in data
    assert "message" not in data


def test_get_logger_called_twice_returns_same_configured_logger():
    """Calling get_logger twice with same name should not duplicate handlers."""
    logger1 = get_logger("singleton-test")
    logger2 = get_logger("singleton-test")
    assert logger1 is logger2
    assert len(logger1.handlers) == 1  # not doubled
