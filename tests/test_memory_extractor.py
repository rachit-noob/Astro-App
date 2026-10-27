import pytest

from app.memory_extractor import extract_memories


def as_pairs(message):
    return {(c.category, c.value) for c in extract_memories(message)}


def test_extracts_goal_and_language_from_one_sentence():
    pairs = as_pairs("I'm planning to switch jobs next year, and I prefer advice in Hindi.")

    assert ("career_goal", "I'm planning to switch jobs next year") in pairs
    assert ("language_preference", "Hindi") in pairs


def test_extracts_profile_facts_and_interests():
    pairs = as_pairs("My name is Rahul and I live in Prayagraj. I love cricket, astrology and cooking.")

    assert ("name", "Rahul") in pairs
    assert ("location", "Prayagraj") in pairs
    assert {("interest", "cricket"), ("interest", "astrology"), ("interest", "cooking")} <= pairs


def test_extracts_birth_details_without_splitting_on_time_decimal():
    pairs = as_pairs("I was born on 5 March 1995 at 5.30 pm in Delhi.")

    assert ("astro_profile", "I was born on 5 March 1995 at 5.30 pm in Delhi") in pairs


@pytest.mark.parametrize(
    "message",
    [
        "What should I focus on for my career?",
        "Why do you say that?",
        "Thanks, that was helpful!",
        "Tell me about my day",
    ],
)
def test_nothing_is_extracted_from_questions_and_small_talk(message):
    assert extract_memories(message) == []


def test_later_statement_in_same_message_wins():
    candidates = extract_memories("I prefer advice in Hindi. Actually I prefer advice in Tamil.")

    languages = [c.value for c in candidates if c.category == "language_preference"]
    assert languages == ["Tamil"]
