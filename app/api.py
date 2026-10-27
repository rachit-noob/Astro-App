from fastapi import FastAPI

from app.chat_service import ChatService
from app.config import Settings
from app.database import Database
from app.llm import LLMClient, OpenAICompatibleClient
from app.memory_store import MemoryStore
from app.schemas import ChatRequest, ChatResponse, MemoryOut


def create_app(settings: Settings | None = None, llm: LLMClient | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    llm = llm or OpenAICompatibleClient(
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        timeout=settings.llm_timeout,
    )
    db = Database(settings.db_path)
    service = ChatService(db, llm, settings)
    memory_store = MemoryStore(db)

    api = FastAPI(title="MyNaksh Personalized Chat")

    @api.post("/chat", response_model=ChatResponse)
    def chat(request: ChatRequest) -> ChatResponse:
        return service.handle(request)

    @api.get("/users/{user_id}/memories", response_model=list[MemoryOut])
    def list_memories(user_id: str) -> list[MemoryOut]:
        return [
            MemoryOut(
                category=m.category,
                value=m.value,
                confidence=m.confidence,
                updated_at=m.updated_at,
            )
            for m in memory_store.list_for_user(user_id)
        ]

    @api.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return api
