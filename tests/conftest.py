import pytest
from fastapi.testclient import TestClient

from app.api import create_app
from app.config import Settings
from app.llm import LLMUnavailableError


class MockLLM:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.available = True

    def generate(self, system_prompt, history, user_message):
        if not self.available:
            raise LLMUnavailableError("mock outage")
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "history": list(history),
                "user_message": user_message,
            }
        )
        return f"mock reply {len(self.calls)}"


@pytest.fixture
def llm() -> MockLLM:
    return MockLLM()


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(db_path=str(tmp_path / "test.db"), history_limit=4, memory_limit=6)


@pytest.fixture
def client(settings, llm) -> TestClient:
    return TestClient(create_app(settings=settings, llm=llm))


@pytest.fixture
def send(client):
    def _send(message, user_id="user-123", session_id="session-1"):
        return client.post(
            "/chat",
            json={"user_id": user_id, "session_id": session_id, "message": message},
        )

    return _send
