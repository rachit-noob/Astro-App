from datetime import datetime, timezone

from app.database import Database


class HistoryStore:
    def __init__(self, db: Database) -> None:
        self.db = db

    def recent(self, user_id: str, session_id: str, limit: int) -> list[dict[str, str]]:
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT role, content FROM messages "
                "WHERE user_id = ? AND session_id = ? "
                "ORDER BY id DESC LIMIT ?",
                (user_id, session_id, limit),
            ).fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]

    def add_turn(self, user_id: str, session_id: str, user_message: str, assistant_message: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.db.connection() as conn:
            conn.executemany(
                "INSERT INTO messages (user_id, session_id, role, content, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                [
                    (user_id, session_id, "user", user_message, now),
                    (user_id, session_id, "assistant", assistant_message, now),
                ],
            )
