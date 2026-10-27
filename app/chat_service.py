from app.config import Settings
from app.database import Database
from app.history import HistoryStore
from app.llm import LLMClient, LLMUnavailableError
from app.memory_extractor import extract_memories
from app.memory_store import MemoryStore
from app.prompts import build_fallback_reply, build_system_prompt
from app.retriever import retrieve_relevant
from app.schemas import ChatRequest, ChatResponse


class ChatService:
    def __init__(self, db: Database, llm: LLMClient, settings: Settings) -> None:
        self.llm = llm
        self.settings = settings
        self.memories = MemoryStore(db)
        self.history = HistoryStore(db)

    def handle(self, request: ChatRequest) -> ChatResponse:
        self.memories.upsert(request.user_id, extract_memories(request.message))

        relevant = retrieve_relevant(
            request.message,
            self.memories.list_for_user(request.user_id),
            self.settings.memory_limit,
        )
        recent = self.history.recent(
            request.user_id, request.session_id, self.settings.history_limit
        )

        fallback = False
        try:
            reply = self.llm.generate(build_system_prompt(relevant), recent, request.message)
            self.history.add_turn(request.user_id, request.session_id, request.message, reply)
        except LLMUnavailableError:
            reply = build_fallback_reply(relevant)
            fallback = True

        return ChatResponse(
            user_id=request.user_id,
            session_id=request.session_id,
            response=reply,
            context_used=list(dict.fromkeys(memory.category for memory in relevant)),
            fallback=fallback,
        )
