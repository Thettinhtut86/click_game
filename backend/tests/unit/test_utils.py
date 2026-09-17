import uuid

from click_game.state.rooms import RoomStore


def test_room_id_normalization():
    room = RoomStore.ensure({
        "players": [{"id": uuid.uuid4(), "name": "Alice", "color": "red"}],
    })
    assert isinstance(room["players"][0]["id"], str)


def test_room_defaults():
    result = RoomStore.ensure({})
    assert result["players"] == []
    assert result["watchers"] == []
    assert result["game_started"] is False
    assert result["option"] == "asc"


def test_room_existing_players_are_serialized():
    result = RoomStore.ensure({
        "players": [{"id": 123, "name": "player1", "color": "red"}],
    })
    assert result["players"][0] == {
        "id": "123",
        "name": "player1",
        "color": "red",
    }


def test_room_existing_host_is_preserved():
    result = RoomStore.ensure({
        "host": "99",
        "players": [{"id": 1, "name": "Alice"}],
    })
    assert result["host"] == "99"
