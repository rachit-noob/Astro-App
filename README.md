# MyNaksh Personalized AI Chat

A small FastAPI service that chats with a user through an LLM, keeps a short window of recent conversation per session, saves useful facts about the user as long-term memory in SQLite, and retrieves only the relevant memories before each LLM call.

## Quick start

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Configure an LLM (any OpenAI-compatible provider):

```bash
export LLM_API_KEY=""
export LLM_MODEL="gpt-5-mini"
export LLM_BASE_URL="https://api.openai.com/v1"
```

Run:

```bash
uvicorn app.main:app --reload
```

Interactive docs: http://127.0.0.1:8000/docs

Run the tests (no API key or network needed, the LLM is mocked):

```bash
pytest
```

### Configuration

All settings are environment variables. See `.env.example`.

| Variable | Default | Meaning |
|---|---|---|
| `LLM_API_KEY` | empty | Provider API key. If empty, the service runs in fallback mode (see below) |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | Any OpenAI-compatible base URL (OpenAI, Groq, Together, Ollama at `http://localhost:11434/v1`, Gemini's OpenAI endpoint, and so on) |
| `LLM_MODEL` | `gpt-4o-mini` | Model name |
| `DB_PATH` | `mynaksh.db` | SQLite file |
| `HISTORY_LIMIT` | `6` | Number of recent messages (3 turns) sent to the LLM |
| `MEMORY_LIMIT` | `6` | Max memories placed in the prompt |

## API

### `POST /chat`

Request:

```json
{
  "user_id": "user-123",
  "session_id": "session-456",
  "message": "What should I focus on for my career?"
}
```

Response:

```json
{
  "user_id": "user-123",
  "session_id": "session-456",
  "response": "...",
  "context_used": ["career_goal", "language_preference"],
  "fallback": false
}
```

`context_used` lists the memory categories that were put into the LLM prompt. `fallback` is an extension to the required format, and is `true` when the LLM could not be reached.

### `GET /users/{user_id}/memories`

Lists everything saved for a user. This is for inspection and debugging.

### `GET /health`

Returns `{"status": "ok"}`.

## Sample session

These are real outputs from running the service. The `response` text below comes from fallback mode, because this run had no `LLM_API_KEY`. With a key configured, `response` is the LLM's generated answer, but `context_used` and the saved memories are identical, since those are decided by this service and not by the LLM.

**1. Statement containing two facts**

```bash
curl -X POST localhost:8000/chat -H 'Content-Type: application/json' -d '{
  "user_id": "user-123",
  "session_id": "session-456",
  "message": "I'"'"'m planning to switch jobs next year, and I prefer advice in Hindi."
}'
```

```json
{
  "user_id": "user-123",
  "session_id": "session-456",
  "response": "I'm unable to reach the AI model right now, so I can't give a full answer. Please try again shortly. Meanwhile, here is what I have saved that may be relevant: career_goal: I'm planning to switch jobs next year; language_preference: Hindi.",
  "context_used": ["career_goal", "language_preference"],
  "fallback": true
}
```

**2. An interest is saved, but it is not pulled into career answers**

Message: `I also love cricket and cooking.` saves two `interest` memories.

**3. Same session, career question**

Message: `What should I focus on for my career?`

```json
{
  "context_used": ["career_goal", "language_preference"]
}
```

The cricket and cooking interests are not in the context.

**4. New session, recall question**

Message (`session-789`): `What do you remember about my career plans?`

```json
{
  "user_id": "user-123",
  "session_id": "session-789",
  "context_used": ["career_goal", "language_preference"]
}
```

**5. What is stored (`GET /users/user-123/memories`)**

```json
[
  {"category": "interest", "value": "cooking", "confidence": 0.8, "updated_at": "..."},
  {"category": "interest", "value": "cricket", "confidence": 0.8, "updated_at": "..."},
  {"category": "language_preference", "value": "Hindi", "confidence": 0.95, "updated_at": "..."},
  {"category": "career_goal", "value": "I'm planning to switch jobs next year", "confidence": 0.85, "updated_at": "..."}
]
```

**6. Validation**

A blank message returns HTTP 422.

## Architecture

```
POST /chat
   │
   ▼
ChatService.handle
   1. extract_memories(message)        rules decide what is worth remembering
   2. MemoryStore.upsert               save or update the user's memories
   3. retrieve_relevant(message, ...)  pick only memories relevant to this question
   4. HistoryStore.recent              last N messages of this session
   5. build_system_prompt(memories)    prompt with the selected memories only
   6. LLMClient.generate               provider call
   7. HistoryStore.add_turn            save user message and reply
   ▼
ChatResponse (response + context_used)
```

```
app/
  api.py               FastAPI app factory and routes
  main.py              uvicorn entrypoint (app = create_app())
  chat_service.py      orchestrates the flow above
  llm.py               LLMClient protocol and OpenAI-compatible implementation
  memory_extractor.py  decides what to remember from a message
  memory_store.py      SQLite persistence for memories
  retriever.py         scores and selects relevant memories
  history.py           SQLite persistence for recent conversation
  prompts.py           system prompt and fallback text
  database.py          schema and connection handling
  schemas.py           request and response models
  config.py            environment-based settings
tests/                 pytest suite with a mock LLM
```

Each module has one job and is easy to replace. The LLM sits behind a two-line `LLMClient` protocol, so switching provider means writing one class. Tests inject a `MockLLM` through `create_app(settings, llm)`.

### Storage

SQLite with two tables:

- `messages(user_id, session_id, role, content, created_at)` holds conversation history. Only the last `HISTORY_LIMIT` messages of a session are read back, so the whole conversation is never sent to the LLM. History is scoped by both `user_id` and `session_id`.
- `memories(user_id, category, slot, value, confidence, created_at, updated_at)` holds long-term memory, with `UNIQUE(user_id, category, slot)`.

### Memory storage: what gets remembered

`memory_extractor.py` is rule-based and runs on every user message:

1. The message is split into sentences and clauses (`, and I ...` becomes a new clause).
2. Questions are discarded, whether they end in `?` or start with a wh-word. This is the main guard against storing every message.
3. Each remaining clause is matched against patterns:

| Category | Example trigger |
|---|---|
| `career_goal`, `relationship_goal`, `finance_goal`, `health_goal` | first person, plus an intent word (plan, want, switching...), plus a topic word (job, marriage, house, weight...) |
| `language_preference` | a known language name plus a preference word (prefer, reply, advice, switch to...) |
| `interest` | "I love / like / enjoy / am interested in ..." |
| `name`, `location`, `occupation` | "my name is", "I live in", "I work as" |
| `astro_profile` | birth details ("I was born on ..."), sun, moon, rising or zodiac sign |

Plain small talk such as "thanks" or "ok" matches nothing and is never stored.

**Slots and corrections.** Each memory has a `slot`. Single-valued facts (career goal, language, name...) use the category as the slot, so a new statement **updates** the old one instead of adding a duplicate. This gives correction handling for free:

> "I prefer advice in Hindi" followed later by "Actually I prefer advice in English" leaves one `language_preference` memory with value `English`.

Interests are multi-valued, so the slot is the interest itself (`cricket`, `cooking`).

**Confidence.** Each memory carries a confidence score. Explicit phrasing such as "I prefer" scores higher than a looser match. Confidence also scales the retrieval score.

### Memory retrieval: how relevant memories are chosen

`retriever.py` scores every memory of the user against the current question and keeps the top `MEMORY_LIMIT` with a score above zero:

- **Topic match (+3).** Query words are mapped to topics (career, relationship, finance, health, astro, interests), and each topic owns certain memory categories. "What should I focus on for my career?" selects `career_goal` and `occupation`.
- **Always-include (+1).** `language_preference` and `name` are cross-cutting, so they apply to any answer.
- **Keyword overlap (+1 per shared word, max 3).** Content words are compared with the memory's text, with light stemming (`jobs` becomes `job`). This lets "Will cricket be lucky for me?" surface the cricket interest even with no topic match.
- **Broad recall (+1).** "What do you remember about me?" with no specific topic gives every memory a small boost, so the user's profile is returned.
- The final score is multiplied by confidence.

Because a memory is included only when it scores above zero, unrelated memories are left out. A career question never sees birth details or cricket. Selected memories are placed in the system prompt as `- category: value` lines, and the prompt tells the model to use them only when relevant and to answer "what do you remember" strictly from them.

### Design decisions and trade-offs

- **Rules instead of an LLM for extraction.** Deterministic, free, fast, easy to test, and it works without an API key. The cost is recall: phrasing outside the patterns is missed. An LLM extractor could be added behind the same `extract_memories` function signature without touching the rest of the pipeline.
- **Keyword retrieval instead of embeddings.** The assignment allows it, and for a small set of per-user memories it is predictable and explainable. `context_used` shows exactly why something was included.
- **Memory is extracted before retrieval.** "I'm switching jobs, what should I focus on?" works in one message.
- **A new connection per operation.** Simple, and safe with FastAPI's threadpool for sync endpoints. Fine at this scale, and a connection pool would be the next step.
- **The assistant reply is saved to history only on success**, so a failed LLM call never leaves a user message with no reply.

### Fallback when the LLM is unavailable

If the key is missing, the provider errors, times out, or returns an empty reply, `/chat` still returns HTTP 200 with `fallback: true` and a short apology that lists the relevant saved memories. Memory extraction has already run by then, so nothing the user said is lost.

