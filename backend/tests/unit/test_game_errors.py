import pytest

from click_game.services.game_service import GameService


def test_wrong_bubble_is_rejected():
    service = GameService()
    room = {}

    service.start(room)

    result = service.select_bubble(
        room,
        "1",
        "B100",
        "#fff",
    )

    assert result["status"] == "wrong_bubble"
    assert result["message"] == ("You must click B1 next! Wrong clicks: 1/3")
    assert result["wrong_clicks"] == 1
    assert result["expected"] == "B1"


def test_game_over_is_rejected():
    service = GameService()

    room = {
        "index": 1,
        "play_order": [1],
        "bubbles": {"B1": None},
    }

    with pytest.raises(ValueError, match="Game is over"):
        service.select_bubble(
            room,
            "1",
            "B1",
            "#fff",
        )
