from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from click_game.services.websocket_service import WebSocketService
from click_game.state.chat import chat_state
from click_game.state.connections import connection_store
from click_game.state.rooms import room_store


@pytest.fixture(autouse=True)
def clean_state():
    connection_store.connections.clear()
    room_store.clear()
    chat_state.typing_users.clear()
    yield
    connection_store.connections.clear()
    room_store.clear()
    chat_state.typing_users.clear()


@pytest.mark.asyncio
async def test_handshake():
    service = WebSocketService()
    service.chat_service.mark_seen = MagicMock()
    ws = AsyncMock()

    with patch.object(service, "_WebSocketService__unused", create=True), \
         patch("click_game.services.websocket_service.websocket_manager.send", new_callable=AsyncMock) as send, \
         patch("click_game.services.websocket_service.websocket_manager.broadcast_online_users", new_callable=AsyncMock) as online, \
         patch("click_game.services.websocket_service.websocket_manager.broadcast_rooms", new_callable=AsyncMock) as rooms:
        await service.handshake(ws, "1", "Alice", {})

    send.assert_awaited_once()
    assert send.await_args.args[1]["action"] == "handshake_ack"
    service.chat_service.mark_seen.assert_called_once_with("1")
    online.assert_awaited_once()
    rooms.assert_awaited_once()


@pytest.mark.asyncio
async def test_unknown_action():
    service = WebSocketService()
    ws = AsyncMock()

    with patch("click_game.services.websocket_service.websocket_manager.send", new_callable=AsyncMock) as send:
        await service.dispatch(ws, "1", "Alice", {"action": "UNKNOWN"})

    message = send.await_args.args[1]
    assert message["action"] == "error"
    assert "Unknown action" in message["message"]


@pytest.mark.asyncio
async def test_join_missing_room_id():
    service = WebSocketService()
    ws = AsyncMock()

    with patch("click_game.services.websocket_service.websocket_manager.send", new_callable=AsyncMock) as send:
        await service.join_room(ws, "1", "Alice", {})

    assert send.await_args.args[1] == {"action": "error", "message": "roomId required"}


@pytest.mark.asyncio
async def test_leave_missing_room_id():
    service = WebSocketService()
    ws = AsyncMock()

    with patch("click_game.services.websocket_service.websocket_manager.send", new_callable=AsyncMock) as send:
        await service.leave_room(ws, "1", "Alice", {})

    assert send.await_args.args[1] == {"action": "error", "message": "roomId required"}


@pytest.mark.asyncio
async def test_leave_missing_room():
    service = WebSocketService()
    ws = AsyncMock()

    with patch("click_game.services.websocket_service.websocket_manager.send", new_callable=AsyncMock) as send:
        await service.leave_room(ws, "1", "Alice", {"roomId": "999"})

    assert send.await_args.args[1]["message"] == "Room not found"


@pytest.mark.asyncio
async def test_leave_active_game_rejected():
    service = WebSocketService()
    ws = AsyncMock()
    room_store.set("1", {"game_started": True})

    with patch("click_game.services.websocket_service.websocket_manager.send", new_callable=AsyncMock) as send:
        await service.leave_room(ws, "1", "Alice", {"roomId": "1"})

    assert "Cannot leave room while game is active" in send.await_args.args[1]["message"]


@pytest.mark.asyncio
async def test_get_rooms():
    service = WebSocketService()
    ws = AsyncMock()
    service.rooms.list_rooms = MagicMock(return_value=[])

    with patch("click_game.services.websocket_service.websocket_manager.send", new_callable=AsyncMock) as send:
        await service.get_rooms(ws, "1", "Alice", {})

    assert send.await_args.args[1] == {"action": "rooms_update", "rooms": []}


@pytest.mark.asyncio
async def test_typing_start_and_stop():
    service = WebSocketService()
    ws = AsyncMock()

    with patch("click_game.services.websocket_service.websocket_manager.broadcast", new_callable=AsyncMock) as broadcast:
        await service.typing_start(ws, "1", "Alice", {})
        await service.typing_stop(ws, "1", "Alice", {})

    assert broadcast.await_count == 2
    assert "1" not in chat_state.typing_users


@pytest.mark.asyncio
async def test_create_room_success():
    service = WebSocketService()
    ws = AsyncMock()
    service.room_service.create = MagicMock(return_value=("10", {"host": "1"}))

    with patch("click_game.services.websocket_service.websocket_manager.send", new_callable=AsyncMock) as send, \
         patch("click_game.services.websocket_service.websocket_manager.broadcast_room_update", new_callable=AsyncMock):
        await service.create_room(ws, "1", "Alice", {"option": "asc"})

    assert send.await_args.args[1]["action"] == "room_created"


@pytest.mark.asyncio
async def test_create_room_failure():
    service = WebSocketService()
    ws = AsyncMock()
    service.room_service.create = MagicMock(side_effect=RuntimeError("DB"))

    with patch("click_game.services.websocket_service.websocket_manager.send", new_callable=AsyncMock) as send:
        await service.create_room(ws, "1", "Alice", {})

    assert send.await_args.args[1] == {"action": "error", "message": "Failed to create room"}


@pytest.mark.asyncio
async def test_send_message():
    service = WebSocketService()
    ws = AsyncMock()
    service.chat_service.send = MagicMock(return_value={
        "id": 1,
        "mentions": ["Bob"],
        "text": "hello @Bob",
    })

    with patch("click_game.services.websocket_service.websocket_manager.broadcast", new_callable=AsyncMock) as broadcast:
        await service.send_message(ws, "1", "Alice", {"text": "hello @Bob"})

    assert broadcast.await_count == 2


@pytest.mark.asyncio
async def test_load_chat():
    service = WebSocketService()
    ws = AsyncMock()
    service.chat_service.history = MagicMock(return_value=[])

    with patch("click_game.services.websocket_service.websocket_manager.send", new_callable=AsyncMock) as send:
        await service.load_chat(ws, "1", "Alice", {})

    assert send.await_args.args[1]["action"] == "init_chat"


@pytest.mark.asyncio
async def test_delete_and_restore_message():
    service = WebSocketService()
    ws = AsyncMock()
    service.chat_service.delete = MagicMock(return_value=True)
    service.chat_service.restore = MagicMock(return_value=True)

    with patch("click_game.services.websocket_service.websocket_manager.broadcast", new_callable=AsyncMock) as broadcast:
        await service.delete_message(ws, "1", "Alice", {"message_id": 1})
        await service.restore_message(ws, "1", "Alice", {"message_id": 1})

    assert broadcast.await_count == 2
