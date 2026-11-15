"""Health endpoint: the process is up AND the database file opens (used by the platform check)."""

import sqlite3

from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from app.db.connection import connect_readonly
from app.dependencies import SettingsDep

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str


@router.get("/health", response_model=HealthResponse)
def health(settings: SettingsDep, response: Response) -> HealthResponse:
    try:
        conn = connect_readonly(settings.database_path)
        try:
            conn.execute("SELECT 1 FROM sqlite_master LIMIT 1")
        finally:
            conn.close()
    except (OSError, sqlite3.Error):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="database_unavailable")
    return HealthResponse(status="ok")
