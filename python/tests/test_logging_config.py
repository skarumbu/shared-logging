import json
import logging
import sys
import io
import pytest

sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))
from shared_logging import get_logger


def _capture_log(logger_name, fn):
    """Call fn(logger) and return the parsed JSON from the formatter output."""
    import uuid
    # Use a unique name each time to avoid shared-state issues between tests
    unique_name = f"{logger_name}-{uuid.uuid4().hex[:8]}"
    logger = get_logger(unique_name)
    buf = io.StringIO()
    # Replace the StreamHandler's stream (not the handler itself) so _JSONFormatter is still used
    logger.handlers[0].stream = buf
    fn(logger)
    output = buf.getvalue().strip()
    return json.loads(output)


def test_get_logger_returns_logger():
    logger = get_logger("test-returns")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test-returns"


def test_request_log_has_required_fields():
    data = _capture_log("req", lambda log: log.info(
        "", extra={"event": "request", "endpoint": "/test", "method": "GET",
                   "status": 200, "duration_ms": 50.0}
    ))
    assert data["event"] == "request"
    assert data["service"].startswith("req-")
    assert data["endpoint"] == "/test"
    assert data["method"] == "GET"
    assert data["status"] == 200
    assert data["duration_ms"] == 50.0
    assert "timestamp" in data
    assert "message" not in data  # no message on request logs


def test_error_log_has_required_fields():
    data = _capture_log("err", lambda log: log.error(
        "", extra={"event": "error", "endpoint": "/test", "method": "POST",
                   "status": 500, "message": "boom", "error_type": "ValueError",
                   "stack_trace": "line 1\nline 2", "duration_ms": 12.3}
    ))
    assert data["event"] == "error"
    assert data["error_type"] == "ValueError"
    assert data["stack_trace"] == "line 1\nline 2"
    assert data["message"] == "boom"


def test_none_fields_are_omitted():
    data = _capture_log("omit", lambda log: log.info(
        "", extra={"event": "request", "endpoint": "/test", "method": "GET",
                   "status": 200, "duration_ms": 10.0}
    ))
    assert "stack_trace" not in data
    assert "error_type" not in data
    assert "message" not in data


def test_get_logger_called_twice_returns_same_configured_logger():
    name = "singleton-test-fixed"
    logger1 = get_logger(name)
    logger2 = get_logger(name)
    assert logger1 is logger2
    assert len(logger1.handlers) == 1  # not doubled


def test_non_serializable_extra_does_not_crash():
    """json.dumps with default=str should handle non-serializable values."""
    from datetime import datetime as dt
    data = _capture_log("serial", lambda log: log.info(
        "", extra={"event": "request", "endpoint": "/test", "method": "GET",
                   "status": 200, "duration_ms": 1.0,
                   "error_type": dt(2026, 1, 1)}  # datetime, not normally serializable
    ))
    # Should not raise; error_type should be stringified
    assert "error_type" in data


import azure.functions as func
from shared_logging import log_request


def _make_request(method="GET", url="http://localhost/api/health"):
    return func.HttpRequest(
        method=method,
        url=url,
        headers={},
        params={},
        route_params={},
        body=b"",
    )


def test_log_request_logs_200_as_request_event():
    name = f"func-ok-{__import__('uuid').uuid4().hex[:6]}"
    logger = get_logger(name)
    buf = io.StringIO()
    logger.handlers[0].stream = buf

    @log_request(logger)
    def handler(req):
        return func.HttpResponse("ok", status_code=200)

    handler(_make_request())
    data = json.loads(buf.getvalue().strip())
    assert data["event"] == "request"
    assert data["status"] == 200
    assert data["method"] == "GET"
    assert "duration_ms" in data


def test_log_request_logs_4xx_as_error_event():
    name = f"func-4xx-{__import__('uuid').uuid4().hex[:6]}"
    logger = get_logger(name)
    buf = io.StringIO()
    logger.handlers[0].stream = buf

    @log_request(logger)
    def handler(req):
        return func.HttpResponse("not found", status_code=404)

    handler(_make_request())
    data = json.loads(buf.getvalue().strip())
    assert data["event"] == "error"
    assert data["status"] == 404


def test_log_request_logs_exception_and_reraises():
    name = f"func-exc-{__import__('uuid').uuid4().hex[:6]}"
    logger = get_logger(name)
    buf = io.StringIO()
    logger.handlers[0].stream = buf

    @log_request(logger)
    def handler(req):
        raise ValueError("boom")

    with pytest.raises(ValueError):
        handler(_make_request())

    data = json.loads(buf.getvalue().strip())
    assert data["event"] == "error"
    assert data["error_type"] == "ValueError"
    assert "boom" in data["message"]
    assert "stack_trace" in data
    assert data["status"] == 500


from fastapi import FastAPI
from fastapi.testclient import TestClient
from shared_logging import fastapi_middleware


def test_fastapi_middleware_logs_request():
    import uuid
    app = FastAPI()
    svc_name = f"fastapi-{uuid.uuid4().hex[:6]}"
    fastapi_middleware(app, service_name=svc_name)

    @app.get("/items")
    def items():
        return {"items": []}

    client = TestClient(app)
    # Capture by redirecting the logger's handler stream
    logger = get_logger(svc_name)
    buf = io.StringIO()
    logger.handlers[0].stream = buf

    client.get("/items")
    lines = [l for l in buf.getvalue().strip().split("\n") if l]
    assert len(lines) >= 1
    data = json.loads(lines[-1])
    assert data["event"] == "request"
    assert data["service"] == svc_name
    assert data["endpoint"] == "/items"
    assert data["status"] == 200


def test_fastapi_middleware_logs_error_for_5xx():
    import uuid
    app = FastAPI()
    svc_name = f"fastapi-err-{uuid.uuid4().hex[:6]}"
    fastapi_middleware(app, service_name=svc_name)

    @app.get("/boom")
    def boom():
        raise ValueError("broke")

    client = TestClient(app, raise_server_exceptions=False)
    logger = get_logger(svc_name)
    buf = io.StringIO()
    logger.handlers[0].stream = buf

    client.get("/boom")
    lines = [l for l in buf.getvalue().strip().split("\n") if l]
    data = json.loads(lines[-1])
    assert data["event"] == "error"
    assert data["error_type"] == "ValueError"
