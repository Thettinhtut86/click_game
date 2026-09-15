import pytest

from click_game.services.game_service import GameService


def test_wrong_bubble_is_rejected():
    service = GameService()
    room = {}
    service.start(room)

    with pytest.raises(ValueError, match="must click B1"):
        service.select_bubble(room, "1", "B100", "#fff")
