"""FastAPI dependencies. Override `get_llm_client` in tests to inject a fake."""

from typing import Annotated

from fastapi import Depends, Request

from app.config import Settings
from app.services.llm.client import LlmClient, build_llm_client
from app.services.pipeline import Pipeline


def get_app_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


SettingsDep = Annotated[Settings, Depends(get_app_settings)]


def get_llm_client(request: Request, settings: SettingsDep) -> LlmClient:
    """One client per app, built lazily, so the HTTP connection pool (and TLS session) is reused."""
    client: LlmClient | None = getattr(request.app.state, "llm_client", None)
    if client is None:
        client = build_llm_client(settings)
        request.app.state.llm_client = client
    return client


def get_pipeline(
    request: Request, settings: SettingsDep, llm: Annotated[LlmClient, Depends(get_llm_client)]
) -> Pipeline:
    return Pipeline(
        llm=llm,
        db_path=settings.database_path,
        max_rows=settings.max_rows,
        timeout_seconds=settings.query_timeout_seconds,
        cache=request.app.state.answer_cache,
    )


PipelineDep = Annotated[Pipeline, Depends(get_pipeline)]
