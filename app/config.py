import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    db_path: str = "mynaksh.db"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_timeout: float = 30.0
    history_limit: int = 6
    memory_limit: int = 6

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            db_path=os.getenv("DB_PATH", cls.db_path),
            llm_api_key=os.getenv("LLM_API_KEY", cls.llm_api_key),
            llm_base_url=os.getenv("LLM_BASE_URL", cls.llm_base_url).rstrip("/"),
            llm_model=os.getenv("LLM_MODEL", cls.llm_model),
            llm_timeout=float(os.getenv("LLM_TIMEOUT", cls.llm_timeout)),
            history_limit=int(os.getenv("HISTORY_LIMIT", cls.history_limit)),
            memory_limit=int(os.getenv("MEMORY_LIMIT", cls.memory_limit)),
        )
