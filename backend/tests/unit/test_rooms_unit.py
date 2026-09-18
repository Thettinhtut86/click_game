from unittest.mock import MagicMock

import pytest

from click_game.repositories.player_repository import PlayerRepository
from click_game.repositories.room_repository import RoomRepository
from click_game.services.room_service import RoomService
from click_game.state.rooms import RoomStore, room_store


@pytest.fixture(autouse=True)
def clear_rooms():
    room_store.clear()
    yield
    room_store.clear()


def test_room_store_ensure_defaults():
    room = RoomStore.ensure({})
    assert room["players"] == []
    assert room["watchers"] == []
    assert room["game_started"] is False
    assert room["option"] == "asc"
    assert room["bubbles"] == {}
    assert room["index"] == 0
    assert room["play_order"] == []
    assert room["display_order"] == []


def test_room_store_ensure_assigns_first_player_as_host():
    room = RoomStore.ensure({
        "players": [{"id": 123, "name": "Alice", "color": "red"}],
    })
    assert room["host"] == "123"
    assert room["players"][0]["id"] == "123"


def test_room_store_ensure_keeps_existing_host():
    room = RoomStore.ensure({
        "host": "99",
        "players": [{"id": 1, "name": "Alice"}],
    })
    assert room["host"] == "99"


def test_room_store_get_set_pop():
    store = RoomStore()
    room = {"host": "1"}
    store.set("1", room)
    assert store.get(1) is room
    assert store.pop("1") is room
    assert store.get("1") is None


def test_room_store_clear():
    store = RoomStore()
    store.set("1", {})
    store.clear()
    assert list(store.all()) == []


def test_room_service_list_rooms():
    rooms = MagicMock(spec=RoomRepository)
    rooms.list_rooms.return_value = [{"id": 1}]
    service = RoomService(MagicMock(spec=PlayerRepository), rooms)
    assert service.list_rooms() == [{"id": 1}]


def test_room_service_create():
    players = MagicMock(spec=PlayerRepository)
    players.get.return_value = {"id": "1", "name": "Alice", "color": "red"}
    rooms = MagicMock(spec=RoomRepository)
    rooms.create.return_value = 10

    room_id, room = RoomService(players, rooms).create("1", "Alice", "desc")

    assert room_id == "10"
    assert room["host"] == "1"
    assert room["option"] == "desc"
    assert room["players"][0]["color"] == "red"
    players.update_room.assert_called_once_with("1", "10")


def test_room_service_create_invalid_option_defaults_to_asc():
    players = MagicMock(spec=PlayerRepository)
    players.get.return_value = {"id": "1", "name": "Alice", "color": "red"}
    rooms = MagicMock(spec=RoomRepository)
    rooms.create.return_value = 10

    _, room = RoomService(players, rooms).create("1", "Alice", "invalid")
    assert room["option"] == "asc"


def test_room_service_create_failure():
    players = MagicMock(spec=PlayerRepository)
    rooms = MagicMock(spec=RoomRepository)
    rooms.create.return_value = None

    with pytest.raises(RuntimeError, match="Failed to create room"):
        RoomService(players, rooms).create("1", "Alice", "asc")


def test_room_service_join_player():
    players = MagicMock(spec=PlayerRepository)
    players.get.return_value = {"id": "2", "name": "Bob", "color": "blue"}
    rooms = MagicMock(spec=RoomRepository)

    room_store.set("1", RoomStore.ensure({
        "host": "1",
        "players": [{"id": "1", "name": "Alice", "color": "red"}],
    }))

    kind, room = RoomService(players, rooms).join("1", "2", "Bob")
    assert kind == "player"
    assert room["players"][-1]["id"] == "2"
    players.update_room.assert_called_once_with("2", "1")


def test_room_service_join_duplicate_player():
    players = MagicMock(spec=PlayerRepository)
    rooms = MagicMock(spec=RoomRepository)
    room_store.set("1", RoomStore.ensure({
        "host": "1",
        "players": [{"id": "1", "name": "Alice", "color": "red"}],
    }))

    kind, _ = RoomService(players, rooms).join("1", "1", "Alice")
    assert kind == "player"
    players.update_room.assert_not_called()


def test_room_service_join_watcher_when_full():
    players = MagicMock(spec=PlayerRepository)
    rooms = MagicMock(spec=RoomRepository)
    room_store.set("1", RoomStore.ensure({
        "host": "1",
        "players": [{"id": str(i), "name": f"P{i}", "color": None} for i in range(4)],
    }))

    kind, room = RoomService(players, rooms).join("1", "5", "Watcher")
    assert kind == "watcher"
    assert room["watchers"] == [{"id": "5", "name": "Watcher"}]


def test_room_service_join_existing_watcher_is_not_duplicated():
    players = MagicMock(spec=PlayerRepository)
    rooms = MagicMock(spec=RoomRepository)
    room_store.set("1", RoomStore.ensure({
        "host": "1",
        "players": [{"id": str(i), "name": f"P{i}", "color": None} for i in range(4)],
        "watchers": [{"id": "5", "name": "Watcher"}],
    }))

    kind, room = RoomService(players, rooms).join("1", "5", "Watcher")
    assert kind == "watcher"
    assert len(room["watchers"]) == 1


def test_room_service_join_missing_room():
    with pytest.raises(ValueError, match="Room not found"):
        RoomService.join(1, "missing-room")


def test_room_service_join_started_room():
    room_store.set("1", RoomStore.ensure({"game_started": True}))
    with pytest.raises(ValueError, match="Game already started"):
        RoomService(MagicMock(), MagicMock()).join("1", "2", "Bob")


def test_remove_player_keeps_non_empty_room():
    players = MagicMock(spec=PlayerRepository)
    rooms = MagicMock(spec=RoomRepository)
    room_store.set("1", RoomStore.ensure({
        "players": [{"id": "1"}, {"id": "2"}],
        "watchers": [],
    }))

    RoomService(players, rooms).remove_player("1", "1")
    assert [p["id"] for p in room_store.get("1")["players"]] == ["2"]
    players.update_room.assert_called_once_with("1", None)
    rooms.delete.assert_not_called()


def test_remove_last_player_deletes_room():
    players = MagicMock(spec=PlayerRepository)
    rooms = MagicMock(spec=RoomRepository)
    room_store.set("1", RoomStore.ensure({"players": [{"id": "1"}], "watchers": []}))

    RoomService(players, rooms).remove_player("1", "1")
    assert room_store.get("1") is None
    rooms.delete.assert_called_once_with("1")


def test_remove_watcher():
    players = MagicMock(spec=PlayerRepository)
    rooms = MagicMock(spec=RoomRepository)
    room_store.set("1", RoomStore.ensure({
        "players": [{"id": "2"}],
        "watchers": [{"id": "1", "name": "Watcher"}],
    }))

    RoomService(players, rooms).remove_player("1", "1")
    assert room_store.get("1")["watchers"] == []


def test_close_room():
    players = MagicMock(spec=PlayerRepository)
    rooms = MagicMock(spec=RoomRepository)
    room_store.set("1", RoomStore.ensure({"players": [{"id": "1"}]}))

    closed = RoomService(players, rooms).close("1")
    assert closed is not None
    assert room_store.get("1") is None
    rooms.delete.assert_called_once_with("1")
    rooms.clear_players.assert_called_once_with("1")


def test_close_missing_room():
    result = RoomService(MagicMock(), MagicMock()).close("999")
    assert result is None
