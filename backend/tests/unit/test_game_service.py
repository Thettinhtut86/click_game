from click_game.services.game_service import GameService


def test_ascending_order():
    service = GameService()
    assert service.generate_play_order("asc") == list(range(1, 101))


def test_descending_order():
    service = GameService()
    assert service.generate_play_order("desc") == list(range(100, 0, -1))


def test_display_order_contains_all_bubbles():
    service = GameService()
    order = service.generate_display_order()
    assert sorted(order) == list(range(1, 101))


def test_select_bubble():
    service = GameService()
    room = {"option": "asc"}
    service.start(room)

    finished = service.select_bubble(
        room,
        "1",
        "B1",
        "#fff",
    )

    assert finished is False
    assert room["index"] == 1
    assert room["bubbles"]["B1"]["uid"] == "1"
