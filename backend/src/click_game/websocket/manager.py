import json
import logging

from fastapi import WebSocket

from click_game.repositories.player_repository import PlayerRepository
from click_game.repositories.room_repository import RoomRepository
from click_game.state.connections import connection_store
from click_game.state.rooms import room_store

logger = logging.getLogger(__name__)


class WebSocketManager:
    async def send(self, websocket: WebSocket, message: dict) -> None:
        await websocket.send_text(json.dumps(message))

    async def broadcast(self, message: dict) -> None:
        dead = []
        for user_id, websocket in list(connection_store.all()):
            try:
                await self.send(websocket, message)
            except Exception:
                dead.append(user_id)

        for user_id in dead:
            connection_store.disconnect_by_id(user_id)

    async def broadcast_room_members(self, room: dict, message: dict) -> None:
        """Broadcast to a captured room snapshot, useful before removing a room."""
        targets = {str(p["id"]) for p in room.get("players", [])}
        targets.update(str(w["id"]) for w in room.get("watchers", []))
        for user_id in targets:
            websocket = connection_store.get(user_id)
            if websocket:
                try:
                    await self.send(websocket, message)
                except Exception:
                    logger.exception("Failed sending to user %s", user_id)

    async def broadcast_room(self, room_id: str, message: dict) -> None:
        room = room_store.get(room_id)
        if not room:
            return

        targets = {
            str(p["id"]) for p in room.get("players", [])
        }
        targets.update(
            str(w["id"]) for w in room.get("watchers", [])
        )

        for user_id in targets:
            websocket = connection_store.get(user_id)
            if websocket:
                try:
                    await self.send(websocket, message)
                except Exception:
                    logger.exception("Failed sending to user %s", user_id)

    async def broadcast_rooms(self) -> None:
        rooms = room_store_database_data()
        await self.broadcast({"action": "rooms_update", "rooms": rooms})

    async def broadcast_room_update(self, room_id: str) -> None:
        room = room_store.get(room_id)
        if not room:
            return

        message = {
            "action": "room_update",
            "roomId": str(room_id),
            "players": [
                {
                    "id": str(p["id"]),
                    "name": p.get("name"),
                    "color": p.get("color"),
                }
                for p in room.get("players", [])
            ],
            "watchers": room.get("watchers", []),
            "hostId": str(room["host"]) if room.get("host") else None,
        }
        await self.broadcast(message)

    async def broadcast_online_users(self) -> None:
        users = PlayerRepository().get_online(connection_store.ids())
        await self.broadcast({"action": "online_users", "users": users})

    async def close_all(self) -> None:
        for _, websocket in list(connection_store.all()):
            try:
                await websocket.close()
            except Exception:
                pass
        for user_id in connection_store.ids():
            connection_store.disconnect_by_id(user_id)


def room_store_database_data() -> list[dict]:
    rows = RoomRepository().list_rooms()
    for room in rows:
        if room.get("created_at") and hasattr(room["created_at"], "strftime"):
            room["created_at"] = room["created_at"].strftime("%Y-%m-%d %H:%M:%S")
    return rows


websocket_manager = WebSocketManager()
