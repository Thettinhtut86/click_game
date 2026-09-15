from click_game.services.auth_service import AuthService


class FakePlayers:
    def __init__(self):
        self.rows = []

    def get_all(self):
        return self.rows

    def insert(self, name, color):
        return 1


def test_login_assigns_color():
    service = AuthService(FakePlayers())
    player = service.login("Alice")

    assert player["id"] == 1
    assert player["name"] == "Alice"
    assert player["color"]
