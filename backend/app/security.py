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
}
API_CSP = "default-src 'none'; frame-ancestors 'none'"
# The bundled UI: same-origin scripts/connections only; inline styles are needed by the
# syntax highlighter and component style props.
APP_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'"
)


def add_security_headers(app: FastAPI) -> None:
    @app.middleware("http")
    async def security_headers_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        is_docs = request.url.path.startswith(_DOCS_PATHS)
        is_api = request.url.path.startswith("/api")
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        if not is_docs:
            response.headers.setdefault("Content-Security-Policy", API_CSP if is_api else APP_CSP)
        if is_api:
            response.headers.setdefault("Cache-Control", "no-store")
        return response
