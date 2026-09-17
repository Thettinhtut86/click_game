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
    finished = service.select_bubble(room, "1", "B1", "#fff")
    assert finished is False
    assert room["index"] == 1
    assert room["bubbles"]["B1"]["uid"] == "1"
    assert room["bubbles"]["B1"]["color"] == "#fff"


def test_select_wrong_bubble():
    service = GameService()
    room = {"option": "asc"}
    service.start(room)
    with pytest.raises(ValueError, match="must click B1"):
        service.select_bubble(room, "1", "B100", "#fff")


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
