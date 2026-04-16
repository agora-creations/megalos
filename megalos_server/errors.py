"""Error vocabulary, size caps, and response helper for megalos MCP server."""

SESSION_NOT_FOUND = "session_not_found"
INVALID_ARGUMENT = "invalid_argument"
OVERSIZE_PAYLOAD = "oversize_payload"
SCHEMA_VIOLATION = "schema_violation"
SESSION_CAP_EXCEEDED = "session_cap_exceeded"
WORKFLOW_NOT_LOADED = "workflow_not_loaded"
UNKNOWN_ARTIFACT = "unknown_artifact"
OUT_OF_ORDER_SUBMISSION = "out_of_order_submission"
SESSION_ESCALATED = "session_escalated"
WORKFLOW_COMPLETE = "workflow_complete"
CONCURRENT_WRITE_CONFLICT = "concurrent_write_conflict"  # reserved for S02

CONTENT_MAX = 262_144
ARTIFACT_MAX = 1_048_576
YAML_MAX = 512_000


def error_response(code: str, error: str, **fields: object) -> dict:
    """Return {"status": "error", "code": code, "error": error, **fields}."""
    return {"status": "error", "code": code, "error": error, **fields}
