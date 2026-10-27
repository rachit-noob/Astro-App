import re

from app.memory_store import Memory


def stem(word: str) -> str:
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def stems(words: set[str]) -> frozenset[str]:
    return frozenset(stem(word) for word in words)


STOP_WORDS = stems({
    "the", "and", "but", "for", "with", "that", "this", "what", "which", "who", "how", "why",
    "when", "where", "you", "your", "are", "was", "were", "has", "have", "had", "can", "could",
    "should", "would", "will", "about", "from", "into", "onto", "does", "did", "not", "also",
    "tell", "please", "know", "remember", "recall", "plan", "planning", "want", "wish", "hope",
    "like", "love", "going", "think", "thinking", "need", "advice", "focus", "help", "prefer",
    "user", "said", "any", "some", "all", "give", "make", "much", "more", "most", "very",
    "just", "now", "then", "there", "their", "them", "they", "his", "her", "its", "our",
})

TOPICS: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    "career": (
        stems({"career", "job", "jobs", "work", "profession", "promotion", "salary", "office",
               "boss", "business", "startup", "resume", "interview", "company", "colleague",
               "employment", "resign", "appraisal"}),
        frozenset({"career_goal", "occupation"}),
    ),
    "relationship": (
        stems({"love", "marriage", "married", "marry", "relationship", "partner", "wedding",
               "spouse", "dating", "girlfriend", "boyfriend", "romance"}),
        frozenset({"relationship_goal"}),
    ),
    "finance": (
        stems({"money", "finance", "financial", "invest", "investment", "savings", "wealth",
               "house", "property", "income", "loan", "debt", "stocks", "flat"}),
        frozenset({"finance_goal"}),
    ),
    "health": (
        stems({"health", "fitness", "weight", "illness", "diet", "sleep", "exercise", "healthy"}),
        frozenset({"health_goal"}),
    ),
    "astro": (
        stems({"horoscope", "kundli", "birth", "born", "chart", "zodiac", "sign", "planet",
               "planets", "dasha", "moon", "sun", "rising", "birthday", "birthplace"}),
        frozenset({"astro_profile"}),
    ),
    "interests": (
        stems({"interest", "interests", "hobby", "hobbies", "passion", "enjoy"}),
        frozenset({"interest"}),
    ),
}

ALWAYS_INCLUDE = frozenset({"language_preference", "name"})
RECALL_PATTERN = re.compile(r"\b(?:remember|recall|know about me|what do you know|about me)\b")

TOPIC_WEIGHT = 3.0
ALWAYS_WEIGHT = 1.0
RECALL_WEIGHT = 1.0
MAX_OVERLAP = 3


def tokenize(text: str) -> frozenset[str]:
    tokens = set()
    for word in re.findall(r"[a-z]+", text.lower()):
        if len(word) < 3:
            continue
        stemmed = stem(word)
        if stemmed not in STOP_WORDS:
            tokens.add(stemmed)
    return frozenset(tokens)


def detect_topic_categories(query_tokens: frozenset[str]) -> frozenset[str]:
    categories: set[str] = set()
    for keywords, topic_categories in TOPICS.values():
        if keywords & query_tokens:
            categories |= topic_categories
    return frozenset(categories)


def score_memory(
    memory: Memory,
    query_tokens: frozenset[str],
    topic_categories: frozenset[str],
    broad_recall: bool,
) -> float:
    score = 0.0
    if memory.category in topic_categories:
        score += TOPIC_WEIGHT
    if memory.category in ALWAYS_INCLUDE:
        score += ALWAYS_WEIGHT
    if broad_recall:
        score += RECALL_WEIGHT
    score += min(len(query_tokens & tokenize(memory.value)), MAX_OVERLAP)
    return score * memory.confidence


def retrieve_relevant(query: str, memories: list[Memory], limit: int) -> list[Memory]:
    query_tokens = tokenize(query)
    topic_categories = detect_topic_categories(query_tokens)
    broad_recall = bool(RECALL_PATTERN.search(query.lower())) and not topic_categories
    scored = [
        (score_memory(memory, query_tokens, topic_categories, broad_recall), memory)
        for memory in memories
    ]
    ranked = sorted(
        (item for item in scored if item[0] > 0),
        key=lambda item: (item[0], item[1].updated_at),
        reverse=True,
    )
    return [memory for _, memory in ranked[:limit]]
