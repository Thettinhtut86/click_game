from click_game.db.database import execute, fetch_all, fetch_one


class RoomRepository:
    def create(self, host_id: str) -> int | None:
        return execute(
            "INSERT INTO rooms (host_id, created_at) VALUES (%s, NOW())",
            (host_id,),
            commit=True,
        )

    def get(self, room_id: str) -> dict | None:
        return fetch_one(
            "SELECT * FROM rooms WHERE id=%s",
            (room_id,),
        )

    def delete(self, room_id: str) -> None:
        execute("DELETE FROM rooms WHERE id=%s", (room_id,), commit=True)

    def set_started(self, room_id: str, started: bool) -> None:
        execute(
            "UPDATE rooms SET started=%s WHERE id=%s",
            (int(started), room_id),
            commit=True,
        )

    def set_winner(self, room_id: str, winner_id: str | None) -> None:
        execute(
            "UPDATE rooms SET winner_id=%s, started=0 WHERE id=%s",
            (winner_id, room_id),
            commit=True,
        )

    def clear_players(self, room_id: str) -> None:
        execute(
            "UPDATE players SET room_id=NULL WHERE room_id=%s",
            (room_id,),
            commit=True,
        )

    def list_rooms(self) -> list[dict]:
        return fetch_all(
            """
            SELECT r.id,
                   r.host_id,
                   h.name AS host_name,
                   r.created_at,
                   COUNT(p.id) AS player_count
            FROM rooms r
            LEFT JOIN players p ON p.room_id = r.id
            LEFT JOIN players h ON h.id = r.host_id
            GROUP BY r.id, r.host_id, h.name, r.created_at
            ORDER BY r.id DESC
            """
        )
