import httpx
import pytest

from app.llm import LLMUnavailableError, OpenAICompatibleClient


def make_client(api_key="key"):
    return OpenAICompatibleClient(api_key=api_key, model="test-model", base_url="https://llm.example/v1")


def fake_response(status=200, payload=None):
    request = httpx.Request("POST", "https://llm.example/v1/chat/completions")
    return httpx.Response(status, json=payload, request=request)


def test_builds_chat_completion_request_and_parses_reply(monkeypatch):
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured.update(url=url, headers=headers, json=json)
        return fake_response(payload={"choices": [{"message": {"content": "  namaste  "}}]})

    monkeypatch.setattr(httpx, "post", fake_post)

    reply = make_client().generate("system text", [{"role": "user", "content": "hi"}], "next question")

    assert reply == "namaste"
    assert captured["url"] == "https://llm.example/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer key"
    assert [m["role"] for m in captured["json"]["messages"]] == ["system", "user", "user"]
    assert captured["json"]["messages"][-1]["content"] == "next question"


def test_missing_api_key_is_reported_as_unavailable():
    with pytest.raises(LLMUnavailableError):
        make_client(api_key="").generate("s", [], "hello")


@pytest.mark.parametrize(
    "response",
    [
        fake_response(status=500, payload={"error": "boom"}),
        fake_response(payload={"unexpected": "shape"}),
        fake_response(payload={"choices": [{"message": {"content": "  "}}]}),
    ],
)
def test_bad_provider_responses_are_reported_as_unavailable(monkeypatch, response):
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: response)

    with pytest.raises(LLMUnavailableError):
        make_client().generate("s", [], "hello")
