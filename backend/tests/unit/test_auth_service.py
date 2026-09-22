import pytest

from click_game.services.auth_service import AuthService, MAX_PLAYERS, PLAYER_COLORS


class FakePlayers:
    def __init__(self, rows=None, insert_id=1):
        self.rows = rows or []
        self.insert_id = insert_id
        self.insert_calls = []

    def get_all(self):
        return self.rows

    def insert(self, name, color):
        self.insert_calls.append((name, color))
        return self.insert_id


def test_login_assigns_first_available_color():
    players = FakePlayers()
    player = AuthService(players).login(" Alice ")
    assert player == {"id": 1, "name": "Alice", "color": PLAYER_COLORS[0]}
    assert players.insert_calls == [("Alice", PLAYER_COLORS[0])]


def test_login_rejects_blank_name():
    with pytest.raises(ValueError, match="user_name required"):
        AuthService(FakePlayers()).login("   ")

def test_login_skips_used_colors():
    rows = [{"id": 1, "color": PLAYER_COLORS[0]}]
    player = AuthService(FakePlayers(rows)).login("Bob")
    assert player["color"] == PLAYER_COLORS[1]


def test_login_rejects_when_all_colors_used():
    rows = [{"id": i, "color": color} for i, color in enumerate(PLAYER_COLORS)]
    with pytest.raises(ValueError, match="No colors available"):
        AuthService(FakePlayers(rows)).login("Alice")


def test_login_rejects_failed_insert():
    with pytest.raises(RuntimeError, match="Failed to create player"):
        AuthService(FakePlayers(insert_id=None)).login("Alice")
