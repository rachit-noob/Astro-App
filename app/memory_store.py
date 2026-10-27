from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from app.database import Database
from app.memory_extractor import MemoryCandidate


@dataclass(frozen=True)
class Memory:
    category: str
    slot: str
    value: str
    confidence: float
    updated_at: str


class MemoryStore:
    def __init__(self, db: Database) -> None:
        self.db = db

    def upsert(self, user_id: str, candidates: Iterable[MemoryCandidate]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        rows = [
            (user_id, c.category, c.slot, c.value, c.confidence, now, now)
            for c in candidates
        ]
        if not rows:
            return
        with self.db.connection() as conn:
            conn.executemany(
                "INSERT INTO memories "
                "(user_id, category, slot, value, confidence, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (user_id, category, slot) DO UPDATE SET "
                "value = excluded.value, "
                "confidence = excluded.confidence, "
                "updated_at = excluded.updated_at",
                rows,
            )

    def list_for_user(self, user_id: str) -> list[Memory]:
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT category, slot, value, confidence, updated_at "
                "FROM memories WHERE user_id = ? ORDER BY updated_at DESC, id DESC",
                (user_id,),
            ).fetchall()
        return [
            Memory(r["category"], r["slot"], r["value"], r["confidence"], r["updated_at"])
            for r in rows
        ]
