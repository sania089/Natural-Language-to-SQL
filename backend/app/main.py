"""FastAPI app factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ask, health, schema
from app.config import Settings, get_settings
from app.error_handlers import register_error_handlers
from app.logging_config import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="Natural Language to SQL", version="0.1.0")
    app.state.settings = settings
    register_error_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    for module in (health, ask, schema):
        app.include_router(module.router, prefix="/api")
    return app


app = create_app()
