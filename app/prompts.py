from app.memory_store import Memory

SYSTEM_TEMPLATE = """You are the MyNaksh assistant, a warm and practical astrology-oriented guide.
Give thoughtful, grounded guidance. Never present astrological predictions as certainties, and never invent birth details or other facts about the user.

{memory_section}

Rules:
- Use the saved facts only when they are relevant to the current question.
- If a language_preference is listed, reply in that language.
- If the user asks what you remember, answer only from the saved facts above. If nothing relevant is listed, say you have nothing saved about that yet.
- Use the recent conversation to resolve follow-up questions."""


def format_memories(memories: list[Memory]) -> str:
    if not memories:
        return "Saved facts about the user: none available for this question."
    lines = "\n".join(f"- {memory.category}: {memory.value}" for memory in memories)
    return f"Saved facts about the user:\n{lines}"


def build_system_prompt(memories: list[Memory]) -> str:
    return SYSTEM_TEMPLATE.format(memory_section=format_memories(memories))


def build_fallback_reply(memories: list[Memory]) -> str:
    message = "I'm unable to reach the AI model right now, so I can't give a full answer. Please try again shortly."
    if memories:
        saved = "; ".join(f"{memory.category}: {memory.value}" for memory in memories)
        message += f" Meanwhile, here is what I have saved that may be relevant: {saved}."
    return message
