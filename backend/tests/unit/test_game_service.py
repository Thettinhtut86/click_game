from unittest.mock import patch

import pytest

from click_game.services.game_service import GameService


def test_ascending_order():
    assert GameService().generate_play_order("asc") == list(range(1, 101))


def test_descending_order():
    assert GameService().generate_play_order("desc") == list(range(100, 0, -1))


def test_unknown_option_defaults_to_ascending():
    assert GameService().generate_play_order("anything") == list(range(1, 101))


def test_display_order_contains_all_bubbles():
    order = GameService().generate_display_order()
    assert sorted(order) == list(range(1, 101))


def test_start_initializes_game():
    service = GameService()
    room = {"option": "asc"}
    service.start(room)
    assert room["game_started"] is True
    assert room["index"] == 0
    assert room["play_order"] == list(range(1, 101))
    assert len(room["display_order"]) == 100
    assert len(room["bubbles"]) == 100


def test_start_descending_game():
    room = {"option": "desc"}
    GameService().start(room)
    assert room["play_order"] == list(range(100, 0, -1))


def test_expected_bubble():
    room = {"index": 0, "play_order": [1, 2, 3]}
    assert GameService().expected_bubble(room) == "B1"
    room["index"] = 2
    assert GameService().expected_bubble(room) == "B3"


def test_expected_bubble_after_game():
    room = {"index": 3, "play_order": [1, 2, 3]}
    assert GameService().expected_bubble(room) is None


def test_select_bubble():
    service = GameService()

    room = {"option": "asc"}
    service.start(room)

    result = service.select_bubble(
        room,
        "1",
        "B1",
        "#fff",
    )

    assert result["status"] == "correct"
    assert result["finished"] is False
    assert room["index"] == 1
    assert room["bubbles"]["B1"]["uid"] == "1"
    assert room["bubbles"]["B1"]["color"] == "#fff"


def test_select_wrong_bubble():
    service = GameService()

    room = {"option": "asc"}
    service.start(room)

    result = service.select_bubble(
        room,
        "1",
        "B100",
        "#fff",
    )

    assert result["status"] == "wrong_bubble"
    assert result["wrong_clicks"] == 1
    assert result["expected"] == "B1"
    assert result["message"] == ("You must click B1 next! Wrong clicks: 1/3")


def test_three_wrong_clicks_trigger_delay():
    service = GameService()

    room = {"option": "asc"}
    service.start(room)

    result = service.select_bubble(room, "1", "B100", "#fff")
    assert result["status"] == "wrong_bubble"
    assert result["wrong_clicks"] == 1

    result = service.select_bubble(room, "1", "B99", "#fff")
    assert result["status"] == "wrong_bubble"
    assert result["wrong_clicks"] == 2

    result = service.select_bubble(room, "1", "B98", "#fff")
    assert result["status"] == "click_delayed"
    assert result["remaining"] == 3
    assert result["message"] == ("Too many wrong clicks. Click delayed for 3 seconds.")


def test_click_is_blocked_during_delay():
    service = GameService()

    room = {"option": "asc"}
    service.start(room)

    service.select_bubble(room, "1", "B100", "#fff")
    service.select_bubble(room, "1", "B99", "#fff")
    service.select_bubble(room, "1", "B98", "#fff")

    result = service.select_bubble(
        room,
        "1",
        "B1",
        "#fff",
    )

    assert result["status"] == "click_delayed"
    assert result["remaining"] > 0
    assert "Click delayed" in result["message"]


def test_select_after_game_is_over():
    service = GameService()
    room = {"index": 1, "play_order": [1], "bubbles": {"B1": {"uid": "1", "color": "#fff"}}}
    with pytest.raises(ValueError, match="Game is over"):
        service.select_bubble(room, "1", "B1", "#fff")


def test_calculate_scores():
    room = {
        "bubbles": {
            "B1": {"uid": "1", "color": "red"},
            "B2": {"uid": "1", "color": "red"},
            "B3": {"uid": "2", "color": "blue"},
            "B4": None,
        }
    }
    assert GameService().calculate_scores(room) == {"1": 2, "2": 1}


def test_winners_single():
    room = {
        "bubbles": {
            "B1": {"uid": "1", "color": "red"},
            "B2": {"uid": "1", "color": "red"},
            "B3": {"uid": "2", "color": "blue"},
        }
    }
    assert GameService().winners(room) == ["1"]


def test_winners_tie():
    room = {
        "bubbles": {
            "B1": {"uid": "1", "color": "red"},
            "B2": {"uid": "2", "color": "blue"},
        }
    }
    assert set(GameService().winners(room)) == {"1", "2"}


def test_winners_empty():
    assert GameService().winners({"bubbles": {}}) == []


def test_display_order_is_randomized():
    with patch("click_game.services.game_service.random.shuffle") as shuffle:
        GameService().generate_display_order()
        shuffle.assert_called_once()
