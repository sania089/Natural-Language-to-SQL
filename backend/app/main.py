"""FastAPI app factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import ask, health, schema
from app.config import Settings, get_settings
from app.error_handlers import register_error_handlers
from app.logging_config import configure_logging
from app.security import add_security_headers
from app.services.answer_cache import AnswerCache
from app.services.rate_limiter import SlidingWindowLimiter


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="Natural Language to SQL", version="0.1.0")
    app.state.settings = settings
    app.state.answer_cache = AnswerCache(settings.answer_cache_size)
    app.state.rate_limiter = SlidingWindowLimiter(settings.rate_limit_per_minute)
    register_error_handlers(app)
    add_security_headers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    for module in (health, ask, schema):
        app.include_router(module.router, prefix="/api")
    if settings.static_dir and settings.static_dir.is_dir():
        # Mounted last so /api routes win; the UI uses hash routing, so no SPA fallback needed.
        app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="ui")
    return app


app = create_app()
