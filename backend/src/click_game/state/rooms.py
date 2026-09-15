import logging

from click_game.repositories.player_repository import PlayerRepository
from click_game.repositories.room_repository import RoomRepository

logger = logging.getLogger(__name__)


class RoomStore:
    def __init__(self):
        self.rooms: dict[str, dict] = {}

    def get(self, room_id: str) -> dict | None:
        return self.rooms.get(str(room_id))

    def set(self, room_id: str, room: dict) -> None:
        self.rooms[str(room_id)] = room

    def pop(self, room_id: str) -> dict | None:
        return self.rooms.pop(str(room_id), None)

    def clear(self) -> None:
        self.rooms.clear()

    def all(self):
        return self.rooms.items()

    @staticmethod
    def ensure(room: dict) -> dict:
        room.setdefault("players", [])
        room.setdefault("watchers", [])
        room.setdefault("bubbles", {})
        room.setdefault("game_started", False)
        room.setdefault("option", "asc")
        room.setdefault("host", None)
        room.setdefault("index", 0)
        room.setdefault("play_order", [])
        room.setdefault("display_order", [])

        room["players"] = [
            {
                "id": str(p.get("id")),
                "name": p.get("name"),
                "color": p.get("color"),
            }
            for p in room["players"]
        ]

        if not room["host"] and room["players"]:
            room["host"] = room["players"][0]["id"]

        return room

    def load_from_database(self) -> None:
        room_repo = RoomRepository()
        player_repo = PlayerRepository()

        rows = room_repo.list_rooms()
        for row in rows:
            room_id = str(row["id"])
            players = player_repo.get_by_room(room_id)

            self.set(
                room_id,
                self.ensure(
                    {
                        "host": str(row["host_id"]) if row.get("host_id") else None,
                        "players": [
                            {
                                "id": str(p["id"]),
                                "name": p["name"],
                                "color": p.get("color"),
                            }
                            for p in players
                        ],
                        "watchers": [],
                        "option": "asc",
                        "game_started": bool(row.get("started")),
                        "bubbles": {},
                        "index": 0,
                        "play_order": [],
                        "display_order": [],
                    }
                ),
            )

        logger.info("Recovered %d rooms from DB", len(self.rooms))


room_store = RoomStore()
