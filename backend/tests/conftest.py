from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.db.seed import seed_database
from app.main import create_app


@pytest.fixture(autouse=True)
def _ignore_dotenv(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep tests hermetic: a developer's local .env (real keys, provider) must not leak in."""
    monkeypatch.setitem(Settings.model_config, "env_file", None)


@pytest.fixture(scope="session")
def seeded_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("db") / "test.db"
    seed_database(path)
    return path


@pytest.fixture
def client(seeded_db: Path) -> Iterator[TestClient]:
    app = create_app(Settings(database_path=seeded_db))
    with TestClient(app) as c:
        yield c
