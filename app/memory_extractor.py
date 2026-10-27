import re
from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryCandidate:
    category: str
    slot: str
    value: str
    confidence: float


LANGUAGES = (
    "hindi", "english", "tamil", "telugu", "bengali", "marathi",
    "gujarati", "kannada", "malayalam", "punjabi", "urdu", "hinglish",
)
ZODIAC_SIGNS = (
    "aries", "taurus", "gemini", "cancer", "leo", "virgo", "libra",
    "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
)

SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+|\n+")
CLAUSE_SPLIT = re.compile(r",?\s+(?:and|but)\s+(?=(?:i|i'm|i've|my)\b)", re.IGNORECASE)
LEADING_FILLER = re.compile(r"^(?:(?:hi|hello|hey|namaste|also|so|well|actually|okay|ok)\b[,!\s]*)+", re.IGNORECASE)
QUESTION_START = re.compile(r"^(?:what|why|how|when|where|which|who|whom|whose)\b")

FIRST_PERSON = re.compile(r"\b(?:i|my|we)\b")
INTENT = re.compile(
    r"\b(?:plan|plans|planning|want|wants|hope|hoping|aim|aiming|intend|going to|"
    r"thinking of|thinking about|looking to|looking for|trying to|dream|dreaming|"
    r"preparing|wish|need to|get|getting|would like|will|goal|goals|ambition|"
    r"switch|switching|change|changing|quit|quitting|resign|resigning|"
    r"buying|investing|saving|start|starting)\b"
)

GOAL_PATTERNS = {
    "career_goal": re.compile(
        r"\b(?:job|jobs|career|promotion|business|startup|company|profession|"
        r"resign|resigning|interview|appraisal)\b"
    ),
    "relationship_goal": re.compile(
        r"\b(?:marry|marriage|married|wedding|relationship|partner|girlfriend|"
        r"boyfriend|spouse|find love)\b"
    ),
    "finance_goal": re.compile(
        r"\b(?:buy|buying|purchase|invest|investing|investment|savings|save|saving|"
        r"house|flat|property|loan|wealth|debt|stocks|car)\b"
    ),
    "health_goal": re.compile(
        r"\b(?:health|weight|fitness|diet|exercise|surgery|sleep|healthy|smoking)\b"
    ),
}

LANGUAGE_PATTERN = re.compile(r"\b(" + "|".join(LANGUAGES) + r")\b")
LANGUAGE_TRIGGER = re.compile(
    r"\b(?:prefer|prefers|reply|respond|answer|answers|speak|talk|advice|"
    r"switch to|explain|communicate|write|comfortable|language)\b"
)
EXPLICIT_PREFERENCE = re.compile(r"\b(?:prefer|prefers|always|only)\b")

NAME_PATTERN = re.compile(r"\b(?:my name is|call me|i am called)\s+([a-z]+(?:\s+[a-z]+)?)")
NAME_BREAKS = frozenset({"and", "but", "i", "from", "who", "living", "live", "is", "am", "at", "in", "here", "not"})

LOCATION_PATTERN = re.compile(
    r"\b(?:i(?:'m| am) (?:from|based in|living in)|i (?:live|stay) in|i moved to)\s+([^,]+)"
)
PLACE_BREAKS = frozenset({"and", "but", "since", "because", "for", "currently", "where", "which"})

BIRTH_PATTERN = re.compile(
    r"\b(?:i was born|born on|born in|"
    r"my (?:date of birth|dob|birthday|birth date|birth time|birth place|birthplace) is)\b"
)
SIGNS = "|".join(ZODIAC_SIGNS)
ZODIAC_SELF_PATTERN = re.compile(r"\bi(?:'m| am) (?:an? )?(?:" + SIGNS + r")(?: sign| person)?$")
ZODIAC_SIGN_PATTERN = re.compile(r"\bmy (?:(zodiac|sun|moon|rising) )?sign is (?:an? )?(?:" + SIGNS + r")\b")

OCCUPATION_PATTERN = re.compile(r"\bi(?:'m| am)? (?:working|work) (?:as|at|in|for)\b")

INTEREST_PATTERN = re.compile(
    r"\bi (?:really |also |truly )?(?:love|like|enjoy)\s+(.+)"
    r"|\bi(?:'m| am) (?:really |also )?(?:interested in|into|passionate about|fond of)\s+(.+)"
)
INTEREST_CUT = re.compile(r"\s+(?:because|since|but|when|so|although|which|while)\b")
INTEREST_SPLIT = re.compile(r",|\band\b")

MAX_INTERESTS = 5
MAX_INTEREST_WORDS = 4


def split_clauses(message: str) -> list[str]:
    text = message.replace("\u2019", "'").replace("\u2018", "'")
    clauses = []
    for sentence in SENTENCE_SPLIT.split(text):
        sentence = sentence.strip()
        if not sentence or sentence.endswith("?"):
            continue
        for part in CLAUSE_SPLIT.split(sentence):
            clause = LEADING_FILLER.sub("", part).strip(" .!;,")
            if clause and not QUESTION_START.match(clause.lower()):
                clauses.append(clause)
    return clauses


def take_phrase(text: str, breaks: frozenset[str], limit: int) -> str:
    words = []
    for word in text.split():
        word = word.strip(".,;:!")
        if word in breaks:
            break
        words.append(word)
        if len(words) == limit:
            break
    return " ".join(words)


def match_language(lowered: str) -> list[MemoryCandidate]:
    found = LANGUAGE_PATTERN.search(lowered)
    if not found or not LANGUAGE_TRIGGER.search(lowered):
        return []
    confidence = 0.95 if EXPLICIT_PREFERENCE.search(lowered) else 0.8
    return [MemoryCandidate("language_preference", "language_preference", found.group(1).title(), confidence)]


def match_profile(clause: str, lowered: str) -> list[MemoryCandidate]:
    candidates = []

    name = NAME_PATTERN.search(lowered)
    if name:
        words = []
        for word in name.group(1).split():
            if word in NAME_BREAKS:
                break
            words.append(word)
        if words:
            candidates.append(MemoryCandidate("name", "name", " ".join(words).title(), 0.95))

    location = LOCATION_PATTERN.search(lowered)
    if location:
        place = take_phrase(location.group(1), PLACE_BREAKS, 4)
        if place:
            candidates.append(MemoryCandidate("location", "location", place.title(), 0.9))

    if BIRTH_PATTERN.search(lowered):
        candidates.append(MemoryCandidate("astro_profile", "birth_details", clause, 0.95))

    sign = ZODIAC_SIGN_PATTERN.search(lowered)
    if sign:
        kind = sign.group(1) or "zodiac"
        candidates.append(MemoryCandidate("astro_profile", f"{kind}_sign", clause, 0.9))
    elif ZODIAC_SELF_PATTERN.search(lowered):
        candidates.append(MemoryCandidate("astro_profile", "zodiac_sign", clause, 0.9))

    if OCCUPATION_PATTERN.search(lowered):
        candidates.append(MemoryCandidate("occupation", "occupation", clause, 0.8))

    return candidates


def match_goals(clause: str, lowered: str) -> list[MemoryCandidate]:
    if not INTENT.search(lowered):
        return []
    return [
        MemoryCandidate(category, category, clause, 0.85)
        for category, pattern in GOAL_PATTERNS.items()
        if pattern.search(lowered)
    ]


def match_interests(lowered: str) -> list[MemoryCandidate]:
    found = INTEREST_PATTERN.search(lowered)
    if not found:
        return []
    raw = INTEREST_CUT.split(found.group(1) or found.group(2))[0]
    candidates = []
    for item in INTEREST_SPLIT.split(raw):
        item = " ".join(item.strip(" .!;:").split()[:MAX_INTEREST_WORDS])
        if len(item) >= 3:
            candidates.append(MemoryCandidate("interest", item, item, 0.8))
    return candidates[:MAX_INTERESTS]


def extract_from_clause(clause: str) -> list[MemoryCandidate]:
    lowered = clause.lower()
    language = match_language(lowered)
    candidates = language + match_profile(clause, lowered)
    if FIRST_PERSON.search(lowered):
        candidates.extend(match_goals(clause, lowered))
        if not language:
            candidates.extend(match_interests(lowered))
    return candidates


def extract_memories(message: str) -> list[MemoryCandidate]:
    found: dict[tuple[str, str], MemoryCandidate] = {}
    for clause in split_clauses(message):
        for candidate in extract_from_clause(clause):
            found[(candidate.category, candidate.slot)] = candidate
    return list(found.values())
