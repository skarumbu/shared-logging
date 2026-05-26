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
- `event`: always `"request"` or `"error"`
- `endpoint`: URL path only, no query string
- `stack_trace`: truncated to 2000 characters
- `error_type`: exception class name (Python) or `err.constructor.name` (JS)
- Fields with null/empty values are omitted from output
