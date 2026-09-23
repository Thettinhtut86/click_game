import logging

from fastapi import WebSocket

from click_game.repositories.player_repository import PlayerRepository
from click_game.repositories.room_repository import RoomRepository
from click_game.services.chat_service import ChatService
from click_game.services.game_service import game_service
from click_game.services.room_service import RoomService
from click_game.state.chat import chat_state
from click_game.state.connections import connection_store
from click_game.state.rooms import room_store
from click_game.websocket.manager import websocket_manager

logger = logging.getLogger(__name__)


class WebSocketService:
    def __init__(self):
        self.players = PlayerRepository()
        self.rooms = RoomRepository()
        self.room_service = RoomService(self.players, self.rooms)
        self.chat_service = ChatService()

    def connect(self, user_id: str, websocket: WebSocket):
        connection_store.add(user_id, websocket)

    async def disconnect(self, user_id: str, name: str, websocket: WebSocket):
        chat_state.stop_typing(user_id)
        connection_store.remove_if_same(user_id, websocket)

        await websocket_manager.broadcast(
            {"action": "typing_stop", "uid": user_id, "name": name}
        )

        for room_id, room in list(room_store.all()):
            if str(room.get("host")) == str(user_id):
                closed = self.room_service.close(room_id)
                if closed:
                    await websocket_manager.broadcast_room_members(
                        closed,
                        {
                            "action": "room_closed",
                            "roomId": room_id,
                            "message": "Host disconnected",
                        },
                    )
                break

        await websocket_manager.broadcast_online_users()
        await websocket_manager.broadcast_rooms()

    async def dispatch(
        self,
        websocket: WebSocket,
        user_id: str,
        user_name: str,
        data: dict,
    ):
        action = data.get("action")
        logger.info("WS action=%s from=%s", action, user_id)

        handlers = {
            "handshake": self.handshake,
            "create_room": self.create_room,
            "join_room": self.join_room,
            "leave_room": self.leave_room,
            "start_game": self.start_game,
            "quit_room": self.quit_room,
            "select_bubble": self.select_bubble,
            "send_message": self.send_message,
            "load_chat": self.load_chat,
            "typing_start": self.typing_start,
            "typing_stop": self.typing_stop,
            "delete_message": self.delete_message,
            "restore_message": self.restore_message,
            "get_rooms": self.get_rooms,
        }

        handler = handlers.get(action)

        if not handler:
            await websocket_manager.send(
                websocket,
                {
                    "action": "error",
                    "message": f"Unknown action: {action}",
                },
            )
            return

        await handler(websocket, user_id, user_name, data)

    async def handshake(self, websocket, user_id, name, data):
        await websocket_manager.send(
            websocket,
            {
                "action": "handshake_ack",
                "status": "connected",
                "userId": user_id,
                "userName": name,
            },
        )
        self.chat_service.mark_seen(user_id)
        await websocket_manager.broadcast_online_users()
        await websocket_manager.broadcast_rooms()

    async def create_room(self, websocket, user_id, name, data):
        try:
            room_id, room = self.room_service.create(
                user_id,
                name,
                data.get("option", "asc"),
            )
            await websocket_manager.send(
                websocket,
                {
                    "action": "room_created",
                    "roomId": room_id,
                    "hostId": user_id,
                },
            )
            await websocket_manager.broadcast_room_update(room_id)
        except Exception:
            logger.exception("Failed to create room")
            await websocket_manager.send(
                websocket,
                {"action": "error", "message": "Failed to create room"},
            )

    async def join_room(self, websocket, user_id, name, data):
        room_id = data.get("roomId")
        if not room_id:
            await websocket_manager.send(
                websocket,
                {"action": "error", "message": "roomId required"},
            )
            return

        try:
            kind, room = self.room_service.join(str(room_id), user_id, name)

            if kind == "watcher":
                action = "watcher_joined"
            else:
                action = "join_ack"

            await websocket_manager.send(
                websocket,
                {"action": action, "roomId": str(room_id)},
            )
            await websocket_manager.broadcast_room_update(str(room_id))
            await websocket_manager.broadcast_rooms()

        except ValueError as exc:
            await websocket_manager.send(
                websocket,
                {"action": "error", "message": str(exc)},
            )

    async def leave_room(self, websocket, user_id, name, data):
        room_id = data.get("roomId")
        if not room_id:
            await websocket_manager.send(
                websocket,
                {"action": "error", "message": "roomId required"},
            )
            return

        room = room_store.get(str(room_id))
        if not room:
            await websocket_manager.send(
                websocket,
                {"action": "error", "message": "Room not found"},
            )
            return

        if room.get("game_started"):
            await websocket_manager.send(
                websocket,
                {
                    "action": "error",
                    "message": "Cannot leave room while game is active",
                },
            )
            return

        self.room_service.remove_player(user_id, str(room_id))

        await websocket_manager.send(
            websocket,
            {"action": "leave_ack", "roomId": str(room_id)},
        )
        await websocket_manager.broadcast_rooms()

    async def start_game(self, websocket, user_id, name, data):
        room_id = data.get("roomId")
        if not room_id:
            await websocket_manager.send(
                websocket,
                {"action": "error", "message": "roomId required"},
            )
            return

        room = room_store.get(str(room_id))
        if not room:
            await websocket_manager.send(
                websocket,
                {"action": "error", "message": "Room not found"},
            )
            return

        if str(user_id) != str(room.get("host")):
            await websocket_manager.send(
                websocket,
                {"action": "error", "message": "Only host can start the game"},
            )
            return

        game_service.start(room)
        self.rooms.set_started(str(room_id), True)

        await websocket_manager.broadcast_room(
            str(room_id),
            {
                "action": "game_started",
                "roomId": str(room_id),
                "bubbles": room["bubbles"],
                "players": room["players"],
                "play_order": room["play_order"],
                "display_order": room["display_order"],
                "option": room["option"],
            },
        )

    async def quit_room(self, websocket, user_id, name, data):
        room_id = data.get("roomId") or data.get("room_id")

        if not room_id:
            await websocket_manager.send(
                websocket,
                {"action": "error", "message": "roomId required"},
            )
            return

        room_id = str(room_id)
        room = room_store.get(room_id)

        if not room:
            await websocket_manager.send(
                websocket,
                {"action": "error", "message": "Room not found"},
            )
            return

        if str(user_id) == str(room.get("host")):
            closed = self.room_service.close(room_id)
            if closed:
                await websocket_manager.broadcast_room_members(
                    closed,
                    {
                        "action": "room_closed",
                        "roomId": room_id,
                        "message": "Host has quit. Room closed.",
                    },
                )
            await websocket_manager.broadcast_rooms()
            return

        self.room_service.remove_player(user_id, room_id)
        await websocket_manager.broadcast_rooms()
        await websocket_manager.send(
            websocket,
            {"action": "quit_ack", "roomId": room_id},
        )

    async def select_bubble(self, websocket, user_id, name, data):
        room_id = data.get("roomId") or data.get("room_id")
        bubble_id = data.get("bubble_id")

        if not room_id or not bubble_id:
            await websocket_manager.send(
                websocket,
                {
                    "action": "error",
                    "message": "roomId and bubble_id required",
                },
            )
            return

        room = room_store.get(str(room_id))

        if not room or not room.get("game_started"):
            await websocket_manager.send(
                websocket,
                {
                    "action": "error",
                    "message": "Game not started or room not found",
                },
            )
            return

        player = next(
            (p for p in room["players"] if str(p["id"]) == str(user_id)),
            None,
        )

        if not player:
            await websocket_manager.send(
                websocket,
                {"action": "error", "message": "Player is not in this room"},
            )
            return

        color = player.get("color")
        if not color:
            db_player = self.players.get(user_id)
            color = db_player.get("color") if db_player else None

        if not color:
            color = "#000000"

        player["color"] = color

        try:
            result = game_service.select_bubble(
                room,
                user_id,
                bubble_id,
                color,
            )
        except ValueError as exc:
            await websocket_manager.send(
                websocket,
                {"action": "error", "message": str(exc)},
            )
            return

        if result["status"] == "wrong_bubble":
            await websocket_manager.send(
                websocket,
                {
                    "action": "wrong_bubble",
                    "message": result["message"],
                    "wrong_clicks": result["wrong_clicks"],
                    "expected": result["expected"],
                },
            )
            return

        if result["status"] == "click_delayed":
            await websocket_manager.send(
                websocket,
                {
                    "action": "wrong_bubble",
                    "message": result["message"],
                    "remaining": result["remaining"],
                },
            )
            return

        if result["status"] == "correct":
            await websocket_manager.broadcast_room(
                str(room_id),
                {
                    "action": "update_bubbles",
                    "roomId": str(room_id),
                    "bubbles": room["bubbles"],
                    "currentIndex": room["index"],
                },
            )

            if result["finished"]:
                await self.end_game(
                    room_id,
                    room
                )

    async def end_game(self, room_id: str, room: dict):
        scores = game_service.calculate_scores(room)
        winners = game_service.winners(room)

        winner_players = [
            p for p in room["players"]
            if str(p["id"]) in winners
        ]

        await websocket_manager.broadcast_room(
            room_id,
            {
                "action": "end_game",
                "roomId": room_id,
                "winners": winner_players,
                "is_tie": len(winners) > 1,
                "scores": scores,
            },
        )

        winner_ids = ",".join(winners) if len(winners) > 1 else (
            winners[0] if winners else None
        )

        self.rooms.set_winner(room_id, winner_ids)
        room_store.pop(room_id)
        await websocket_manager.broadcast_rooms()

    async def send_message(self, websocket, user_id, name, data):
        message = self.chat_service.send(
            user_id,
            name,
            data.get("text", ""),
            connection_store.ids(),
        )

        if not message:
            return

        await websocket_manager.broadcast(
            {"action": "new_message", "message": message}
        )

        for mention in message["mentions"]:
            await websocket_manager.broadcast(
                {
                    "action": "mention",
                    "from": name,
                    "to": mention,
                    "message": message["text"],
                }
            )

    async def load_chat(self, websocket, user_id, name, data):
        await websocket_manager.send(
            websocket,
            {
                "action": "init_chat",
                "messages": self.chat_service.history(),
            },
        )

    async def delete_message(self, websocket, user_id, name, data):
        message_id = data.get("message_id")
        if not message_id:
            return

        if self.chat_service.delete(user_id, message_id):
            await websocket_manager.broadcast(
                {
                    "action": "message_deleted",
                    "message_id": message_id,
                }
            )

    async def restore_message(self, websocket, user_id, name, data):
        message_id = data.get("message_id")
        if not message_id:
            return

        if self.chat_service.restore(user_id, message_id):
            await websocket_manager.broadcast(
                {
                    "action": "message_restored",
                    "message_id": message_id,
                }
            )

    async def typing_start(self, websocket, user_id, name, data):
        chat_state.start_typing(user_id)
        await websocket_manager.broadcast(
            {"action": "typing_start", "uid": user_id, "name": name}
        )

    async def typing_stop(self, websocket, user_id, name, data):
        chat_state.stop_typing(user_id)
        await websocket_manager.broadcast(
            {"action": "typing_stop", "uid": user_id, "name": name}
        )

    async def get_rooms(self, websocket, user_id, name, data):
        await websocket_manager.send(
            websocket,
            {
                "action": "rooms_update",
                "rooms": self.rooms.list_rooms(),
            },
        )
