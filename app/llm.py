from typing import Protocol, Sequence

import httpx


class LLMUnavailableError(Exception):
    pass


class LLMClient(Protocol):
    def generate(
        self,
        system_prompt: str,
        history: Sequence[dict[str, str]],
        user_message: str,
    ) -> str: ...


class OpenAICompatibleClient:
    def __init__(self, api_key: str, model: str, base_url: str, timeout: float = 30.0) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout = timeout

    def generate(
        self,
        system_prompt: str,
        history: Sequence[dict[str, str]],
        user_message: str,
    ) -> str:
        if not self.api_key:
            raise LLMUnavailableError("LLM_API_KEY is not configured")
        messages = [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": user_message},
        ]
        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "messages": messages, "temperature": 0.7},
                timeout=self.timeout,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMUnavailableError(str(exc)) from exc
        if not content or not content.strip():
            raise LLMUnavailableError("LLM returned an empty response")
        return content.strip()
