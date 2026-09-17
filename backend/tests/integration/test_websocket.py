import json
from unittest.mock import AsyncMock, patch

import pytest
from starlette.websockets import WebSocketDisconnect

from click_game.core.security import create_access_token


def test_websocket_missing_token(client):
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws"):
            pass
    assert exc.value.code == 1008


def test_websocket_invalid_token(client):
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws?token=invalid"):
            pass
    assert exc.value.code == 1008


def test_websocket_valid_token_handshake(client, valid_token, monkeypatch):
    from click_game.websocket import endpoint

    monkeypatch.setattr(endpoint.service.chat_service, "mark_seen", lambda user_id: None)

    with patch.object(endpoint.service, "connect") as connect, \
         patch("click_game.websocket.endpoint.websocket_manager", create=True), \
         patch("click_game.endpoint", create=True):
        pass

    # Use the actual endpoint manager but suppress its database-dependent broadcasts.
    with patch("click_game.services.websocket_service.websocket_manager.broadcast_online_users", new_callable=AsyncMock), \
         patch("click_game.services.websocket_service.websocket_manager.broadcast_rooms", new_callable=AsyncMock):
        with client.websocket_connect(f"/ws?token={valid_token}") as websocket:
            websocket.send_json({"action": "handshake"})
            response = websocket.receive_json()

    assert response["action"] == "handshake_ack"
    assert response["status"] == "connected"


def test_websocket_unknown_action(client, valid_token):
    with patch("click_game.services.websocket_service.websocket_manager.broadcast_online_users", new_callable=AsyncMock), \
         patch("click_game.services.websocket_service.websocket_manager.broadcast_rooms", new_callable=AsyncMock):
        with client.websocket_connect(f"/ws?token={valid_token}") as websocket:
            websocket.send_json({"action": "unknown_action"})
            response = websocket.receive_json()

    assert response["action"] == "error"
    assert "Unknown action" in response["message"]


def test_websocket_invalid_json(client, valid_token):
    with patch("click_game.services.websocket_service.websocket_manager.broadcast_online_users", new_callable=AsyncMock), \
         patch("click_game.services.websocket_service.websocket_manager.broadcast_rooms", new_callable=AsyncMock):
        with client.websocket_connect(f"/ws?token={valid_token}") as websocket:
            websocket.send_text("INVALID JSON")
            response = websocket.receive_json()

    assert response == {"error": "Invalid JSON format"}


def test_websocket_connection_cleanup(client, valid_token):
    with patch("click_game.services.websocket_service.websocket_manager.broadcast_online_users", new_callable=AsyncMock), \
         patch("click_game.services.websocket_service.websocket_manager.broadcast_rooms", new_callable=AsyncMock):
        with client.websocket_connect(f"/ws?token={valid_token}"):
            pass
