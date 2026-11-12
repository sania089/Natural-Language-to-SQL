"""GET /api/schema: the introspected schema, for the frontend schema browser."""

from fastapi import APIRouter

from app.dependencies import SettingsDep
from app.services.schema import SchemaInfo, get_schema

router = APIRouter(tags=["schema"])


@router.get("/schema", response_model=SchemaInfo)
def schema(settings: SettingsDep) -> SchemaInfo:
    return get_schema(settings.database_path)
