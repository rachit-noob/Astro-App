from app.memory_store import Memory
from app.retriever import retrieve_relevant


def memory(category, value, slot=None, confidence=0.9):
    return Memory(category, slot or category, value, confidence, "2026-01-01T00:00:00")


MEMORIES = [
    memory("career_goal", "I'm planning to switch jobs next year"),
    memory("language_preference", "Hindi"),
    memory("interest", "cricket", slot="cricket"),
    memory("astro_profile", "I was born on 5 March 1995", slot="birth_details"),
    memory("finance_goal", "I want to buy a house"),
]


def categories(query, limit=6):
    return [m.category for m in retrieve_relevant(query, MEMORIES, limit)]


def test_career_question_prioritises_career_goal():
    assert categories("What should I focus on for my career?") == ["career_goal", "language_preference"]


def test_finance_question_does_not_pull_in_career_goal():
    assert categories("Is it a good time to buy property?") == ["finance_goal", "language_preference"]


def test_generic_recall_question_returns_everything_up_to_limit():
    assert len(categories("What do you remember about me?")) == 5
    assert len(categories("What do you remember about me?", limit=2)) == 2


def test_keyword_overlap_can_surface_a_memory_without_a_topic():
    assert "interest" in categories("Will cricket be lucky for me?")


def test_unrelated_question_only_returns_always_included_memories():
    assert categories("What is the weather like today?") == ["language_preference"]
