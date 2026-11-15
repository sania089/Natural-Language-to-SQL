"""Production-readiness: config safety, docs off, daily LLM cap, health, proxy-aware client IP."""

from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.config import Settings
from app.dependencies import get_llm_client
from app.errors import DailyLimitReachedError
from app.main import create_app
from app.services.daily_budget import DailyBudget
from tests.fakes import FakeLlmClient, sql_reply

COUNT = "SELECT COUNT(*) AS n FROM customers"


def _client(db: Path, fake: FakeLlmClient, **overrides: object) -> TestClient:
    app = create_app(Settings(database_path=db, **overrides))  # type: ignore[arg-type]
    app.dependency_overrides[get_llm_client] = lambda: fake
    return TestClient(app, raise_server_exceptions=False)


# --- production config ---


def test_production_requires_the_chosen_providers_key() -> None:
    with pytest.raises(ValidationError, match="GEMINI_API_KEY"):
        Settings(environment="production")
    with pytest.raises(ValidationError, match="GROQ_API_KEY"):
        Settings(environment="production", llm_provider="groq", gemini_api_key="unused")  # type: ignore[arg-type]


def test_production_starts_with_key_and_hides_docs(seeded_db: Path) -> None:
    app = create_app(
        Settings(environment="production", gemini_api_key="k", database_path=seeded_db)
    )  # type: ignore[arg-type]
    c = TestClient(app)
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert c.get(path).status_code == 404


def test_development_keeps_docs(client: TestClient) -> None:
    assert client.get("/docs").status_code == 200


# --- daily budget ---


def test_budget_blocks_after_limit_and_resets_next_day() -> None:
    day = [date(2026, 1, 1)]
    budget = DailyBudget(2, today=lambda: day[0])
    budget.consume()
    budget.consume()
    with pytest.raises(DailyLimitReachedError):
        budget.consume()
    day[0] = date(2026, 1, 2)
    budget.consume()


def test_budget_zero_disables() -> None:
    budget = DailyBudget(0)
    for _ in range(5):
        budget.consume()


def test_daily_limit_returns_503_but_cached_answers_are_free(seeded_db: Path) -> None:
    fake = FakeLlmClient(sql_reply(COUNT), sql_reply(COUNT))
    c = _client(seeded_db, fake, daily_llm_call_limit=1, rate_limit_per_minute=0)
    ask = lambda q: c.post("/api/ask", json={"question": q})  # noqa: E731
    assert ask("how many customers?").status_code == 200
    assert ask("how many customers?").status_code == 200  # cache hit: no LLM call, no budget
    blocked = ask("count the customers please")
    assert blocked.status_code == 503
    assert blocked.json()["error"]["code"] == "DAILY_LIMIT_REACHED"
    assert len(fake.calls) == 1


# --- health ---


def test_health_reports_missing_database(tmp_path: Path) -> None:
    c = TestClient(create_app(Settings(database_path=tmp_path / "missing.db")))
    r = c.get("/api/health")
    assert r.status_code == 503
    assert r.json() == {"status": "database_unavailable"}


# --- proxy-aware client IP ---


def test_rate_limit_is_per_real_client_behind_proxy(seeded_db: Path) -> None:
    app = create_app(Settings(database_path=seeded_db, rate_limit_per_minute=1))
    app.dependency_overrides[get_llm_client] = lambda: FakeLlmClient(*[sql_reply(COUNT)] * 4)
    # Same wrapper uvicorn applies with --proxy-headers --forwarded-allow-ips='*'.
    c = TestClient(ProxyHeadersMiddleware(app, trusted_hosts="*"), raise_server_exceptions=False)

    def ask(ip: str, q: str) -> int:
        return c.post("/api/ask", json={"question": q}, headers={"X-Forwarded-For": ip}).status_code

    assert ask("1.1.1.1", "how many customers a") == 200
    assert ask("1.1.1.1", "how many customers b") == 429  # same user limited
    assert ask("2.2.2.2", "how many customers c") == 200  # different user is not
