from click_game.repositories.player_repository import PlayerRepository


PLAYER_COLORS = [
    "#e6194b", "#3cb44b", "#ffe119", "#437fd8",
    "#f58231", "#440568", "#46f0f0", "#f032e6",
    "#1d0a0a", "#fabebe", "#008080", "#2600ff",
]

MAX_PLAYERS = 12


class AuthService:
    def __init__(self, players: PlayerRepository):
        self.players = players

    def login(self, name: str) -> dict:
        name = name.strip()
        if not name:
            raise ValueError("user_name required")

        players = self.players.get_all()

        if len(players) >= MAX_PLAYERS:
            raise ValueError("Maximum 12 players allowed")

        used = {p["color"] for p in players if p.get("color")}
        available = [c for c in PLAYER_COLORS if c not in used]

        if not available:
            raise ValueError("No colors available")

        color = available[0]
        player_id = self.players.insert(name, color)

        if player_id is None:
            raise RuntimeError("Failed to create player")

        return {
            "id": player_id,
            "name": name,
            "color": color,
        }
