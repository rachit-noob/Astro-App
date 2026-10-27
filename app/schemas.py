from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    session_id: str = Field(min_length=1, max_length=128)
    message: str = Field(max_length=4000)

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message must not be blank")
        return value


class ChatResponse(BaseModel):
    user_id: str
    session_id: str
    response: str
    context_used: list[str]
    fallback: bool = False


class MemoryOut(BaseModel):
    category: str
    value: str
    confidence: float
    updated_at: str
