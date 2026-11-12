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


def get_llm_client(settings: SettingsDep) -> LlmClient:
    return build_llm_client(settings)


def get_pipeline(
    settings: SettingsDep, llm: Annotated[LlmClient, Depends(get_llm_client)]
) -> Pipeline:
    return Pipeline(
        llm=llm,
        db_path=settings.database_path,
        max_rows=settings.max_rows,
        timeout_seconds=settings.query_timeout_seconds,
    )


PipelineDep = Annotated[Pipeline, Depends(get_pipeline)]
