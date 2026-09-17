from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from click_game.repositories.player_repository import PlayerRepository
from click_game.repositories.room_repository import RoomRepository
from click_game.state.connections import connection_store
from click_game.state.rooms import room_store
from click_game.websocket.manager import WebSocketManager


@pytest.fixture(autouse=True)
def clean_state():
    connection_store.connections.clear()
    room_store.clear()
    yield
    connection_store.connections.clear()
    room_store.clear()


@pytest.mark.asyncio
async def test_broadcast_one_client():
    manager = WebSocketManager()
    ws = AsyncMock()
    connection_store.add("1001", ws)

    await manager.broadcast({"type": "test"})

    ws.send_text.assert_called_once()


@pytest.mark.asyncio
async def test_broadcast_multiple_clients():
    manager = WebSocketManager()
    ws1, ws2 = AsyncMock(), AsyncMock()
    connection_store.add("1001", ws1)
    connection_store.add("1002", ws2)

    await manager.broadcast({})

    ws1.send_text.assert_called_once()
    ws2.send_text.assert_called_once()


@pytest.mark.asyncio
async def test_broadcast_disconnected_socket_is_removed():
    manager = WebSocketManager()
    ws = AsyncMock()
    ws.send_text.side_effect = RuntimeError("closed")
    connection_store.add("1001", ws)

    await manager.broadcast({})

    assert connection_store.get("1001") is None


@pytest.mark.asyncio
async def test_broadcast_room_players_and_watchers():
    manager = WebSocketManager()
    player_ws = AsyncMock()
    watcher_ws = AsyncMock()
    other_ws = AsyncMock()

    connection_store.add("1", player_ws)
    connection_store.add("2", watcher_ws)
    connection_store.add("3", other_ws)
    room_store.set("room1", {
        "players": [{"id": "1"}],
        "watchers": [{"id": "2"}],
    })

    await manager.broadcast_room("room1", {"type": "room"})

    player_ws.send_text.assert_called_once()
    watcher_ws.send_text.assert_called_once()
    other_ws.send_text.assert_not_called()


@pytest.mark.asyncio
async def test_broadcast_missing_room():
    manager = WebSocketManager()
    await manager.broadcast_room("missing", {})
    assert connection_store.ids() == []


@pytest.mark.asyncio
async def test_broadcast_room_members_snapshot():
    manager = WebSocketManager()
    ws = AsyncMock()
    connection_store.add("1", ws)

    await manager.broadcast_room_members(
        {"players": [{"id": "1"}], "watchers": []},
        {"action": "room_closed"},
    )

    ws.send_text.assert_called_once()


@pytest.mark.asyncio
@patch("click_game.websocket.manager.RoomRepository")
async def test_broadcast_rooms(mock_repo):
    manager = WebSocketManager()
    mock_repo.return_value.list_rooms.return_value = []
    with patch.object(manager, "broadcast", new_callable=AsyncMock) as broadcast:
        await manager.broadcast_rooms()
    broadcast.assert_awaited_once_with({"action": "rooms_update", "rooms": []})


@pytest.mark.asyncio
async def test_broadcast_room_update():
    manager = WebSocketManager()
    room_store.set("room1", {
        "host": "1",
        "players": [{"id": "1", "name": "Alice", "color": "red"}],
        "watchers": [{"id": "2", "name": "Bob"}],
    })
    with patch.object(manager, "broadcast", new_callable=AsyncMock) as broadcast:
        await manager.broadcast_room_update("room1")

    message = broadcast.await_args.args[0]
    assert message["action"] == "room_update"
    assert message["roomId"] == "room1"
    assert message["hostId"] == "1"


@pytest.mark.asyncio
@patch("click_game.websocket.manager.PlayerRepository")
async def test_broadcast_online_users(mock_repo):
    manager = WebSocketManager()
    mock_repo.return_value.get_online.return_value = [{"id": "1"}]
    connection_store.add("1", AsyncMock())

    with patch.object(manager, "broadcast", new_callable=AsyncMock) as broadcast:
        await manager.broadcast_online_users()

    mock_repo.return_value.get_online.assert_called_once_with(["1"])
    broadcast.assert_awaited_once_with({
        "action": "online_users",
        "users": [{"id": "1"}],
    })


@pytest.mark.asyncio
async def test_close_all():
    manager = WebSocketManager()
    ws1, ws2 = AsyncMock(), AsyncMock()
    connection_store.add("1", ws1)
    connection_store.add("2", ws2)

    await manager.close_all()

    ws1.close.assert_awaited_once()
    ws2.close.assert_awaited_once()
    assert connection_store.ids() == []
