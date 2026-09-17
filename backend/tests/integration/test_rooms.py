from unittest.mock import MagicMock

from click_game.api.routers import rooms


def test_rooms_empty(client, monkeypatch):
    service = MagicMock()
    service.list_rooms.return_value = []
    monkeypatch.setattr(rooms, "service", service)

    response = client.get("/rooms")

    assert response.status_code == 200
    assert response.json() == []


def test_rooms_one_room(client, monkeypatch):
    service = MagicMock()
    service.list_rooms.return_value = [{
        "id": 1,
        "host_id": 1,
        "host_name": "Alice",
        "created_at": "2026-01-01 10:00:00",
        "player_count": 2,
    }]
    monkeypatch.setattr(rooms, "service", service)

    response = client.get("/rooms")

    assert response.status_code == 200
    assert response.json()[0]["id"] == 1


def test_rooms_multiple_rooms(client, monkeypatch):
    service = MagicMock()
    service.list_rooms.return_value = [{"id": 1}, {"id": 2}]
    monkeypatch.setattr(rooms, "service", service)

    response = client.get("/rooms")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_rooms_database_exception(client, monkeypatch):
    service = MagicMock()
    service.list_rooms.side_effect = RuntimeError("DB")
    monkeypatch.setattr(rooms, "service", service)

    response = client.get("/rooms")

    assert response.status_code == 500
    assert response.json()["detail"] == "db error"


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
