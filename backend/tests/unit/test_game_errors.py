import pytest

from click_game.services.game_service import GameService


def test_wrong_bubble_is_rejected():
    service = GameService()
    room = {}
    service.start(room)
    with pytest.raises(ValueError, match="must click B1"):
        service.select_bubble(room, "1", "B100", "#fff")


def test_game_over_is_rejected():
    service = GameService()
    room = {"index": 1, "play_order": [1], "bubbles": {"B1": None}}
    with pytest.raises(ValueError, match="Game is over"):
        service.select_bubble(room, "1", "B1", "#fff")
