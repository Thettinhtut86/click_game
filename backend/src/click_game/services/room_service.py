from click_game.repositories.player_repository import PlayerRepository
from click_game.repositories.room_repository import RoomRepository
from click_game.state.rooms import room_store


class RoomService:
    def __init__(
        self,
        players: PlayerRepository | None = None,
        rooms: RoomRepository | None = None,
    ):
        self.players = players or PlayerRepository()
        self.rooms = rooms or RoomRepository()

    def list_rooms(self):
        return self.rooms.list_rooms()

    def create(self, user_id: str, name: str, option: str) -> tuple[str, dict]:
        room_id = self.rooms.create(user_id)

        if room_id is None:
            raise RuntimeError("Failed to create room")

        room_id = str(room_id)
        self.players.update_room(user_id, room_id)

        player = self.players.get(user_id) or {
            "id": user_id,
            "name": name,
            "color": None,
        }

        room = room_store.ensure(
            {
                "host": str(user_id),
                "option": option if option in {"asc", "desc"} else "asc",
                "players": [
                    {
                        "id": str(user_id),
                        "name": name,
                        "color": player.get("color"),
                    }
                ],
            }
        )
        room_store.set(room_id, room)

        return room_id, room

    def load(self, room_id: str) -> dict | None:
        room = room_store.get(room_id)
        if room:
            return room

        row = self.rooms.get(room_id)
        if not row:
            return None

        players = self.players.get_by_room(room_id)
        room = room_store.ensure(
            {
                "host": str(row["host_id"]),
                "players": players,
                "watchers": [],
            }
        )
        room_store.set(room_id, room)
        return room

    def join(self, room_id: str, user_id: str, name: str) -> tuple[str, dict]:
        room = self.load(room_id)

        if not room:
            raise ValueError("Room not found")

        if room["game_started"]:
            raise ValueError("Game already started")

        if any(str(p["id"]) == str(user_id) for p in room["players"]):
            return "player", room

        if len(room["players"]) >= 4:
            if not any(str(w["id"]) == str(user_id) for w in room["watchers"]):
                room["watchers"].append({"id": str(user_id), "name": name})
            return "watcher", room

        self.players.update_room(user_id, room_id)
        player = self.players.get(user_id) or {
            "id": user_id,
            "name": name,
            "color": None,
        }

        room["players"].append(
            {
                "id": str(user_id),
                "name": name,
                "color": player.get("color"),
            }
        )
        return "player", room

    def remove_player(self, user_id: str, room_id: str | None = None) -> None:
        room_ids = [str(room_id)] if room_id else list(room_store.rooms.keys())

        for rid in room_ids:
            room = room_store.get(rid)
            if not room:
                continue

            room["players"] = [
                p for p in room["players"] if str(p["id"]) != str(user_id)
            ]
            room["watchers"] = [
                w for w in room.get("watchers", [])
                if str(w["id"]) != str(user_id)
            ]

            if not room["players"] and not room["watchers"]:
                room_store.pop(rid)
                self.rooms.delete(rid)

        self.players.update_room(user_id, None)

    def close(self, room_id: str) -> dict | None:
        room = room_store.pop(room_id)
        if room:
            self.rooms.delete(room_id)
            self.rooms.clear_players(room_id)
        return room

    def logout(self, user_id: str) -> None:
        self.remove_player(user_id)
        self.players.delete(user_id)
