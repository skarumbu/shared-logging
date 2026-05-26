# Shared Logging Schema

All services emit one of two JSON event types to stdout.

## Request Log
```json
{
  "event": "request",
  "service": "my-service",
  "endpoint": "/api/path",
  "method": "GET",
  "status": 200,
  "duration_ms": 134.2,
  "timestamp": "2026-05-25T10:00:00.000Z"
}
```

## Error Log
```json
{
  "event": "error",
  "service": "my-service",
  "endpoint": "/api/path",
  "method": "POST",
  "status": 500,
  "message": "Table storage connection failed",
  "error_type": "ServiceRequestError",
  "stack_trace": "Traceback (most recent call last):\n  ...",
  "duration_ms": 45.1,
  "timestamp": "2026-05-25T10:00:01.000Z"
}
```

## Field Reference

| Field | Type | Required | Present On | Notes |
|-------|------|----------|------------|-------|
| `event` | string | Yes | Both | `"request"` or `"error"` |
| `service` | string | Yes | Both | Service name, e.g. `"ideas-api"` |
| `endpoint` | string | Yes (HTTP) | Both | URL path only, no query string. Use descriptive label for non-HTTP (e.g. `/job/name`) |
| `method` | string | Yes | Both | HTTP verb or `"JOB"` / `"DISCORD"` for non-HTTP |
| `status` | integer | Yes | Both | HTTP status code; use `200`/`500` for non-HTTP |
| `duration_ms` | float | Yes | Both | Request duration in milliseconds |
| `timestamp` | string | Yes | Both | ISO 8601 UTC, e.g. `"2026-05-25T10:00:00.000Z"` |
| `message` | string | Yes | error only | Human-readable error description |
| `error_type` | string | Yes | error only | Exception class name |
| `stack_trace` | string | No | error only | Stack trace, truncated to 2000 chars |

Fields with `null` or empty string values are omitted from output.
