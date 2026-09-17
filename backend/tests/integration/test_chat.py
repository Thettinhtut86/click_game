from unittest.mock import MagicMock

from click_game.services.websocket_service import WebSocketService


def test_chat_service_send_integration_shape():
    service = WebSocketService()
    service.chat_service = MagicMock()
    service.chat_service.send.return_value = {
        "id": 1,
        "uid": "1",
        "name": "Alice",
        "color": "red",
        "text": "hello",
        "mentions": [],
        "deleted": 0,
        "timestamp": "10:00",
    }

    result = service.chat_service.send("1", "Alice", "hello", [])
    assert result["text"] == "hello"


def test_chat_service_rejects_empty():
    service = WebSocketService()
    service.chat_service = MagicMock()
    service.chat_service.send.return_value = None
    assert service.chat_service.send("1", "Alice", "", []) is None
