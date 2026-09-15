from click_game.db.database import execute, fetch_all, fetch_one


class ChatRepository:
    def create(
        self,
        player_id: str,
        player_name: str,
        player_color: str,
        message: str,
    ) -> int | None:
        return execute(
            """
            INSERT INTO daily_chat
            (player_id, player_name, player_color, message)
            VALUES (%s,%s,%s,%s)
            """,
            (player_id, player_name, player_color, message),
            commit=True,
        )

    def history_today(self) -> list[dict]:
        return fetch_all(
            """
            SELECT id, player_id, player_name, player_color, message, deleted, created_at
            FROM daily_chat
            WHERE DATE(created_at) = CURDATE()
            ORDER BY id ASC
            """
        )

    def get_owner(self, message_id: int) -> dict | None:
        return fetch_one(
            "SELECT player_id FROM daily_chat WHERE id=%s",
            (message_id,),
        )

    def set_deleted(self, message_id: int, deleted: bool) -> None:
        execute(
            "UPDATE daily_chat SET deleted=%s WHERE id=%s",
            (int(deleted), message_id),
            commit=True,
        )

    def increment_unread(self, user_id: str) -> None:
        execute(
            """
            INSERT INTO chat_unread(user_id, unread_count)
            VALUES (%s,1)
            ON DUPLICATE KEY UPDATE unread_count = unread_count + 1
            """,
            (user_id,),
            commit=True,
        )

    def mark_seen(self, user_id: str) -> None:
        row = fetch_one("SELECT MAX(id) AS last_id FROM daily_chat")
        if not row or row.get("last_id") is None:
            return
        execute(
            """
            UPDATE chat_unread
            SET last_seen=%s
            WHERE user_id=%s
            """,
            (row["last_id"], user_id),
            commit=True,
        )

    def cleanup(self) -> None:
        execute("DELETE FROM daily_chat WHERE created_at < CURDATE()", commit=True)
        execute("DELETE FROM chat_reads", commit=True)
        execute("DELETE FROM chat_unread", commit=True)
