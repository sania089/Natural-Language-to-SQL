"""Central exception -> HTTP mapping, plus request-ID middleware. No internals leak to clients."""

import logging
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.errors import AppError
from app.request_context import request_id_var

log = logging.getLogger(__name__)

_PUBLIC_EXTRA = ("rule",)


def _body(code: str, message: str, extra: dict[str, str] | None = None) -> dict[str, object]:
    error: dict[str, object] = {
        "code": code,
        "message": message,
        "request_id": request_id_var.get(),
    }
    error.update({k: v for k, v in (extra or {}).items() if k in _PUBLIC_EXTRA})
    return {"error": error}


def register_error_handlers(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_id_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        rid = uuid.uuid4().hex[:12]
        token = request_id_var.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = rid
        return response

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        log.info("request failed", extra={"code": exc.code})
        return JSONResponse(_body(exc.code, exc.message, exc.extra), status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            _body("INVALID_REQUEST", "The request body is invalid."), status_code=422
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error")
        return JSONResponse(
            _body("INTERNAL_ERROR", "Something went wrong on our side."), status_code=500
        )
