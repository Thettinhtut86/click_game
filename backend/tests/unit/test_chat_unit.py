from datetime import datetime
from unittest.mock import MagicMock

import pytest

from click_game.repositories.chat_repository import ChatRepository
from click_game.repositories.player_repository import PlayerRepository
from click_game.services.chat_service import ChatService, MAX_MESSAGE_LENGTH


def make_service(player=None):
    chat = MagicMock(spec=ChatRepository)
    players = MagicMock(spec=PlayerRepository)
    players.get.return_value = player
    return ChatService(chat, players), chat, players


def test_send_normal_message():
    service, chat, players = make_service({"color": "red"})
    chat.create.return_value = 10

    message = service.send("1001", "Alice", " hello ", ["1001", "2001"])

    assert message["id"] == 10
    assert message["uid"] == "1001"
    assert message["text"] == "hello"
    assert message["color"] == "red"
    assert message["mentions"] == []
    chat.create.assert_called_once_with("1001", "Alice", "red", "hello")
    chat.increment_unread.assert_called_once_with("2001")


def test_send_empty_message():
    service, chat, _ = make_service()
    assert service.send("1", "Alice", "   ", ["2"]) is None
    chat.create.assert_not_called()


def test_send_too_long_message():
    service, chat, _ = make_service()
    assert service.send("1", "Alice", "x" * (MAX_MESSAGE_LENGTH + 1), ["2"]) is None
    chat.create.assert_not_called()


def test_send_without_player_uses_white():
    service, chat, _ = make_service(None)
    chat.create.return_value = 1
    message = service.send("1", "Alice", "hello", [])
    assert message["color"] == "#ffffff"


def test_send_detects_mentions():
    service, chat, _ = make_service({"color": "red"})
    chat.create.return_value = 1
    message = service.send("1", "Alice", "hello @bob @Alice_1", [])
    assert message["mentions"] == ["bob", "Alice_1"]


def test_send_does_not_increment_sender():
    service, chat, _ = make_service({"color": "red"})
    chat.create.return_value = 1
    service.send("1", "Alice", "hello", ["1"])
    chat.increment_unread.assert_not_called()


def test_history_formats_datetime_and_string():
    service, chat, _ = make_service()
    chat.history_today.return_value = [
        {
            "id": 1,
            "player_id": "1",
            "player_name": "Alice",
            "player_color": "red",
            "message": "hello",
            "deleted": 0,
            "created_at": datetime(2026, 1, 1, 12, 34),
        },
        {
            "id": 2,
            "player_id": "2",
            "player_name": "Bob",
            "player_color": "blue",
            "message": "hi",
            "deleted": 1,
            "created_at": "2026-01-01 13:45:00",
        },
    ]

    assert service.history() == [
        {
            "id": 1,
            "uid": "1",
            "name": "Alice",
            "color": "red",
            "text": "hello",
            "deleted": 0,
            "timestamp": "12:34",
        },
        {
            "id": 2,
            "uid": "2",
            "name": "Bob",
            "color": "blue",
            "text": "hi",
            "deleted": 1,
            "timestamp": "13:45",
        },
    ]


def test_delete_owner():
    service, chat, _ = make_service()
    chat.get_owner.return_value = {"player_id": "1"}
    assert service.delete("1", 10) is True
    chat.set_deleted.assert_called_once_with(10, True)


def test_delete_non_owner():
    service, chat, _ = make_service()
    chat.get_owner.return_value = {"player_id": "2"}
    assert service.delete("1", 10) is False
    chat.set_deleted.assert_not_called()


def test_delete_missing_message():
    service, chat, _ = make_service()
    chat.get_owner.return_value = None
    assert service.delete("1", 10) is False


def test_restore_owner():
    service, chat, _ = make_service()
    chat.get_owner.return_value = {"player_id": "1"}
    assert service.restore("1", 10) is True
    chat.set_deleted.assert_called_once_with(10, False)


def test_restore_non_owner():
    service, chat, _ = make_service()
    chat.get_owner.return_value = {"player_id": "2"}
    assert service.restore("1", 10) is False


def test_mark_seen_delegates():
    service, chat, _ = make_service()
    service.mark_seen("1")
    chat.mark_seen.assert_called_once_with("1")


def test_cleanup_delegates():
    service, chat, _ = make_service()
    service.cleanup()
    chat.cleanup.assert_called_once()
