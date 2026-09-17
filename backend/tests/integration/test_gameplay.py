from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from click_game.services.websocket_service import WebSocketService
from click_game.state.rooms import RoomStore, room_store


@pytest.fixture(autouse=True)
def clear_room():
    room_store.clear()
    yield
    room_store.clear()


@pytest.mark.asyncio
async def test_create_join_start_game_flow():
    service = WebSocketService()
    ws = AsyncMock()

    service.room_service.create = MagicMock(return_value=(
        "1",
        RoomStore.ensure({
            "host": "1",
            "option": "asc",
            "players": [{"id": "1", "name": "Alice", "color": "red"}],
        }),
    ))
    service.room_service.join = MagicMock(return_value=(
        "player",
        RoomStore.ensure({
            "host": "1",
            "players": [
                {"id": "1", "name": "Alice", "color": "red"},
                {"id": "2", "name": "Bob", "color": "blue"},
            ],
        }),
    ))

    with patch("click_game.services.websocket_service.websocket_manager.send", new_callable=AsyncMock), \
         patch("click_game.services.websocket_service.websocket_manager.broadcast_room_update", new_callable=AsyncMock), \
         patch("click_game.services.websocket_service.websocket_manager.broadcast_rooms", new_callable=AsyncMock):
        await service.create_room(ws, "1", "Alice", {"option": "asc"})
        room_store.set("1", service.room_service.create.return_value[1])
        await service.join_room(ws, "2", "Bob", {"roomId": "1"})

    service.room_service.join.assert_called_once_with("1", "2", "Bob")


@pytest.mark.asyncio
async def test_start_game_requires_host():
    service = WebSocketService()
    ws = AsyncMock()
    room_store.set("1", RoomStore.ensure({
        "host": "1",
        "players": [{"id": "1", "name": "Alice", "color": "red"}],
    }))

    with patch("click_game.services.websocket_service.websocket_manager.send", new_callable=AsyncMock) as send:
        await service.start_game(ws, "2", "Bob", {"roomId": "1"})

    assert send.await_args.args[1]["message"] == "Only host can start the game"


@pytest.mark.asyncio
async def test_select_bubble_requires_game():
    service = WebSocketService()
    ws = AsyncMock()
    room_store.set("1", RoomStore.ensure({
        "host": "1",
        "players": [{"id": "1", "name": "Alice", "color": "red"}],
    }))

    with patch("click_game.services.websocket_service.websocket_manager.send", new_callable=AsyncMock) as send:
        await service.select_bubble(ws, "1", "Alice", {"roomId": "1", "bubble_id": "B1"})

    assert "Game not started" in send.await_args.args[1]["message"]
