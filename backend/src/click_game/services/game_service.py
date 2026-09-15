import random


class GameService:
    def generate_display_order(self) -> list[int]:
        numbers = list(range(1, 101))
        random.shuffle(numbers)
        return numbers

    def generate_play_order(self, option: str) -> list[int]:
        if option == "desc":
            return list(range(100, 0, -1))
        return list(range(1, 101))

    def start(self, room: dict) -> None:
        display_order = self.generate_display_order()
        room["play_order"] = self.generate_play_order(room.get("option", "asc"))
        room["display_order"] = display_order
        room["index"] = 0
        room["game_started"] = True
        room["bubbles"] = {f"B{i}": None for i in display_order}

    def expected_bubble(self, room: dict) -> str | None:
        index = room["index"]
        order = room["play_order"]

        if index >= len(order):
            return None

        return f"B{order[index]}"

    def select_bubble(self, room: dict, user_id: str, bubble_id: str, color: str) -> bool:
        expected = self.expected_bubble(room)

        if expected is None:
            raise ValueError("Game is over")

        if bubble_id != expected:
            raise ValueError(f"You must click {expected} next!")

        room["bubbles"][bubble_id] = {
            "uid": str(user_id),
            "color": color,
        }
        room["index"] += 1

        return room["index"] >= len(room["play_order"])

    def calculate_scores(self, room: dict) -> dict[str, int]:
        scores: dict[str, int] = {}

        for owner in room["bubbles"].values():
            if owner:
                uid = str(owner["uid"])
                scores[uid] = scores.get(uid, 0) + 1

        return scores

    def winners(self, room: dict) -> list[str]:
        scores = self.calculate_scores(room)
        if not scores:
            return []

        maximum = max(scores.values())
        return [uid for uid, score in scores.items() if score == maximum]


game_service = GameService()
