from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.dependencies import get_llm_client
from app.main import create_app
from app.services.rate_limiter import SlidingWindowLimiter
from tests.fakes import FakeLlmClient, sql_reply

COUNT = "SELECT COUNT(*) AS n FROM customers"


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_limiter_blocks_then_recovers() -> None:
    clock = Clock()
    limiter = SlidingWindowLimiter(2, 60, clock)
    assert limiter.check("a") is None
    assert limiter.check("a") is None
    assert limiter.check("a") == 60
    assert limiter.check("b") is None  # other clients unaffected
    clock.now = 30
    assert limiter.check("a") == 30
    clock.now = 61
    assert limiter.check("a") is None


def test_limiter_zero_disables() -> None:
    limiter = SlidingWindowLimiter(0)
    assert all(limiter.check("a") is None for _ in range(100))


def _client(db: Path, **overrides: int) -> TestClient:
    app = create_app(Settings(database_path=db, **overrides))  # type: ignore[arg-type]
    app.dependency_overrides[get_llm_client] = lambda: FakeLlmClient(*[sql_reply(COUNT)] * 10)
    return TestClient(app, raise_server_exceptions=False)


def test_ask_is_rate_limited(seeded_db: Path) -> None:
    client = _client(seeded_db, rate_limit_per_minute=2)
    for _ in range(2):
        assert client.post("/api/ask", json={"question": "how many customers?"}).status_code == 200
    r = client.post("/api/ask", json={"question": "how many customers?"})
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "RATE_LIMITED"
    assert int(r.headers["Retry-After"]) >= 1
    assert client.get("/api/health").status_code == 200  # only /ask is limited


def test_security_headers_present(client: TestClient) -> None:
    r = client.get("/api/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'none'" in r.headers["Content-Security-Policy"]


def test_docs_skip_csp(client: TestClient) -> None:
    r = client.get("/docs")
    assert "Content-Security-Policy" not in r.headers
    assert r.headers["X-Content-Type-Options"] == "nosniff"


def test_cors_only_allows_configured_origin(client: TestClient) -> None:
    ok = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    bad = client.get("/api/health", headers={"Origin": "http://evil.example"})
    assert ok.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in bad.headers


@pytest.mark.parametrize("length", [501, 5_001])
def test_overlong_question_rejected(seeded_db: Path, length: int) -> None:
    r = _client(seeded_db).post("/api/ask", json={"question": "a" * length})
    assert r.status_code == 422


def test_static_ui_served_with_app_csp(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<html>ui</html>", encoding="utf-8")
    ui_client = TestClient(create_app(Settings(static_dir=tmp_path)))
    page = ui_client.get("/")
    assert page.status_code == 200
    assert "script-src 'self'" in page.headers["Content-Security-Policy"]
    assert (
        ui_client.get("/api/health")
        .headers["Content-Security-Policy"]
        .startswith("default-src 'none'")
    )
