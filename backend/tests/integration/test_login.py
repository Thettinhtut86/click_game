from unittest.mock import MagicMock

from click_game.api.routers import auth


def test_login_success(client, monkeypatch):
    service = MagicMock()
    service.login.return_value = {"id": 1, "name": "Alice", "color": "red"}
    monkeypatch.setattr(auth, "auth_service", service)

    response = client.post("/login", json={"user_name": "Alice"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["user_id"] == "1"
    assert body["userName"] == "Alice"
    assert body["color"] == "red"
    assert body["token"]


def test_login_invalid_name(client, monkeypatch):
    service = MagicMock()
    service.login.side_effect = ValueError("user_name required")
    monkeypatch.setattr(auth, "auth_service", service)

    response = client.post("/login", json={"user_name": " "})
    assert response.status_code == 400
    assert response.json()["detail"] == "user_name required"


def test_login_service_error(client, monkeypatch):
    service = MagicMock()
    service.login.side_effect = RuntimeError("DB")
    monkeypatch.setattr(auth, "auth_service", service)

    response = client.post("/login", json={"user_name": "Alice"})
    assert response.status_code == 500
    assert response.json()["detail"] == "db error"


def test_login_validation(client):
    response = client.post("/login", json={"user_name": ""})
    assert response.status_code == 422


def test_logout_success(client, monkeypatch):
    room_service = MagicMock()
    monkeypatch.setattr(auth, "room_service", room_service)

    response = client.post("/logout", json={"user_id": "1"})

    assert response.status_code == 200
    assert response.json() == {"status": "logged_out", "userId": "1"}
    room_service.logout.assert_called_once_with("1")


def test_logout_accepts_player_id(client, monkeypatch):
    room_service = MagicMock()
    monkeypatch.setattr(auth, "room_service", room_service)

    response = client.post("/logout", json={"player_id": "2"})

    assert response.status_code == 200
    assert response.json()["userId"] == "2"


def test_logout_missing_uid(client):
    response = client.post("/logout", json={})
    assert response.status_code == 400


def test_logout_undefined_uid(client):
    response = client.post("/logout", json={"user_id": "undefined"})
    assert response.status_code == 400


def test_logout_service_error(client, monkeypatch):
    room_service = MagicMock()
    room_service.logout.side_effect = RuntimeError("DB")
    monkeypatch.setattr(auth, "room_service", room_service)

    response = client.post("/logout", json={"user_id": "1"})
    assert response.status_code == 500
