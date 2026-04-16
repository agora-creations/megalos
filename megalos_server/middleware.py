"""FastMCP middleware that normalizes pydantic.ValidationError to error_response.

FastMCP validates tool arguments against a pydantic model BEFORE the tool body
runs. When that validation fails (None for a required arg, wrong type for a str
arg, etc.) it raises pydantic.ValidationError, which the per-tool _trap_errors
decorator never sees because the body is never entered.

This middleware sits at the framework boundary, catches that exception, and
returns the same {status, code, field, error} shape that _check_str would have
emitted if the call had reached the tool body. The wire-level error contract
is therefore uniform whether the rejection happens in pydantic or in the tool's
own _check_str / size-cap / KeyError handling.

Note: _check_str / _trap_errors / oversize-payload checks in tools.py remain —
they handle empty-string and oversize cases that pydantic doesn't touch, and
serve as belt-and-suspenders for None/wrong-type if this hook is ever bypassed.
"""

from typing import Any

from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext  # type: ignore[import-not-found]
from fastmcp.tools import ToolResult  # type: ignore[attr-defined]
from pydantic import ValidationError

from .errors import error_response


class ValidationErrorMiddleware(Middleware):
    """Convert pydantic.ValidationError raised by tool dispatch to error_response."""

    async def on_call_tool(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, Any],
    ) -> Any:
        try:
            return await call_next(context)
        except ValidationError as exc:
            errs = exc.errors()
            if errs and errs[0].get("loc"):
                field = str(errs[0]["loc"][0])
                msg = str(errs[0].get("msg", str(exc)))
            else:
                field = "unknown"
                msg = str(exc)
            return ToolResult(
                structured_content=error_response("invalid_argument", msg, field=field),
            )
