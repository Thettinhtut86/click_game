from unittest.mock import MagicMock

from click_game.api.routers import auth
from click_game.state.connections import connection_store
from click_game.state.rooms import RoomStore, room_store


def test_logout_success(client, monkeypatch):
    service = MagicMock()
    monkeypatch.setattr(auth, "room_service", service)

    response = client.post("/logout", json={"user_id": "1"})

    assert response.status_code == 200
    service.logout.assert_called_once_with("1")


def test_logout_removes_connection(client, monkeypatch):
    service = MagicMock()
    monkeypatch.setattr(auth, "room_service", service)
    ws = MagicMock()
    connection_store.add("1", ws)

    response = client.post("/logout", json={"user_id": "1"})

    assert response.status_code == 200
    assert connection_store.get("1") is None


def test_logout_removes_player_from_room(client, monkeypatch):
    service = MagicMock()
    monkeypatch.setattr(auth, "room_service", service)
    room_store.set("r1", RoomStore.ensure({
        "host": "2",
        "players": [
            {"id": "1", "name": "Alice"},
            {"id": "2", "name": "Bob"},
        ],
    }))

    response = client.post("/logout", json={"user_id": "1"})

    assert response.status_code == 200
    # The router delegates room membership cleanup to RoomService.
    service.logout.assert_called_once_with("1")
