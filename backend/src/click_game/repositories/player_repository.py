from click_game.db.database import execute, fetch_all, fetch_one


class PlayerRepository:
    def get(self, player_id: str | int) -> dict | None:
        return fetch_one(
            "SELECT id, name, color, room_id FROM players WHERE id=%s",
            (player_id,),
        )

    def get_all(self) -> list[dict]:
        return fetch_all("SELECT id, name, color FROM players")

    def insert(self, name: str, color: str) -> int | None:
        return execute(
            """
            INSERT INTO players (name, joined_at, color)
            VALUES (%s, NOW(), %s)
            """,
            (name, color),
            commit=True,
        )

    def update_room(self, player_id: str, room_id: str | None) -> None:
        execute(
            "UPDATE players SET room_id=%s WHERE id=%s",
            (room_id, player_id),
            commit=True,
        )

    def update_color(self, player_id: str, color: str) -> None:
        execute(
            "UPDATE players SET color=%s WHERE id=%s",
            (color, player_id),
            commit=True,
        )

    def delete(self, player_id: str) -> None:
        execute("DELETE FROM players WHERE id=%s", (player_id,), commit=True)

    def get_by_room(self, room_id: str) -> list[dict]:
        return fetch_all(
            "SELECT id, name, color FROM players WHERE room_id=%s",
            (room_id,),
        )

    def get_online(self, ids: list[str]) -> list[dict]:
        if not ids:
            return []
        placeholders = ",".join(["%s"] * len(ids))
        return fetch_all(
            f"SELECT id, name, color FROM players WHERE id IN ({placeholders})",
            tuple(ids),
        )
