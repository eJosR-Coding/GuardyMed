"""Consistent API error envelope.

Every error response has the same shape::

    {"detail": "<human readable message>", "code": "<machine readable code>"}

Validation errors additionally carry ``fields``: ``[{"field": "...", "message": "..."}]``.
``detail`` stays a plain string so existing clients (and FastAPI conventions) keep working.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

_DEFAULT_CODES = {
    400: "bad_request",
    401: "unauthenticated",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "unprocessable",
    429: "rate_limited",
}


class ApiError(HTTPException):
    """HTTPException that also carries a stable, machine-readable ``code``."""

    def __init__(self, status_code: int, detail: str, *, code: str) -> None:
        super().__init__(status_code=status_code, detail=detail)
        self.code = code


def _code_for(exc: StarletteHTTPException) -> str:
    explicit = getattr(exc, "code", None)
    if explicit:
        return explicit
    return _DEFAULT_CODES.get(exc.status_code, "error" if exc.status_code < 500 else "server_error")


def _field_name(loc: tuple) -> str:
    parts = [str(item) for item in loc if item not in ("body", "query", "path")]
    return ".".join(parts) or "request"


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": str(exc.detail), "code": _code_for(exc)},
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [
            {"field": _field_name(tuple(error.get("loc", ()))), "message": str(error.get("msg", "invalid value"))}
            for error in exc.errors()
        ]
        summary = "; ".join(f"{item['field']}: {item['message']}" for item in fields) or "invalid request"
        return JSONResponse(
            status_code=422,
            content={"detail": f"Validation failed: {summary}", "code": "validation_error", "fields": fields},
        )
