"""Security response headers. The API only serves JSON, so the CSP can be fully locked down."""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

_DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")  # Swagger UI needs scripts/styles: no CSP
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Resource-Policy": "same-site",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Cache-Control": "no-store",
}


def add_security_headers(app: FastAPI) -> None:
    @app.middleware("http")
    async def security_headers_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        is_docs = request.url.path.startswith(_DOCS_PATHS)
        for name, value in SECURITY_HEADERS.items():
            if is_docs and name == "Content-Security-Policy":
                continue
            response.headers.setdefault(name, value)
        return response
