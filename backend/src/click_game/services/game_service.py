import random
import time

class GameService:
    CLICK_DELAY_SECONDS = 3
    WRONG_CLICK_LIMIT = 3

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
        room["wrong_clicks"] = {}
        room["click_delay_until"] = {}

    def _get_remaining_delay(self, room: dict, user_id: str) -> float:
        user_id = str(user_id)

        delay_until = room.get("click_delay_until", {}).get(user_id)
        if delay_until is None:
            return 0.0

        remaining = delay_until - time.monotonic()
        if remaining <= 0:
            # Delay expired
            room["click_delay_until"].pop(user_id, None) 
            return 0.0

        return remaining

    def expected_bubble(self, room: dict) -> str | None:
        index = room["index"]
        order = room["play_order"]

        if index >= len(order):
            return None

        return f"B{order[index]}"

    def select_bubble(self, room: dict, user_id: str, bubble_id: str, color: str) -> dict:
        user_id = str(user_id)
        expected = self.expected_bubble(room)

        if expected is None:
            raise ValueError("Game is over")

        remaining = self._get_remaining_delay(room, user_id)
        if remaining > 0:
            return {
                "status": "click_delayed",
                "message": (
                    f"Click delayed. "
                    f"Try again in {remaining:1f} seconds."
                ),
                "remaining": round(remaining, 1),
            }

        if bubble_id != expected:
            wrong_clicks = room.setdefault("wrong_clicks", {})
            count = wrong_clicks.get(user_id, 0) + 1
            wrong_clicks[user_id] = count

            if count >= self.WRONG_CLICK_LIMIT:
                room.setdefault(
                    "click_delay_until",
                    {},
                )[user_id] =(
                        time.monotonic() + self.CLICK_DELAY_SECONDS
                )

                wrong_clicks[user_id] = 0
                return {
                    "status": "click_delayed",
                    "message": (
                        "Too many wrong clicks. "
                        "Click delayed for "
                        f"{self.CLICK_DELAY_SECONDS} seconds."
                    ),
                    "remaining": self.CLICK_DELAY_SECONDS,
                }
            return {
                "status": "wrong_bubble",
                "message": (
                    f"You must click {expected} next! "
                    f"Wrong clicks: {count}/"
                    f"{self.WRONG_CLICK_LIMIT}"
                ),
                "wrong_clicks": count,
                "expected": expected,
            }

        room.setdefault("wrong_clicks", {})[user_id] = 0

        room["bubbles"][bubble_id] = {
            "uid": str(user_id),
            "color": color,
        }
        room["index"] += 1

        finished = (
            room["index"] >= len(room["play_order"])
        )

        return {
            "status": "correct",
            "finished": finished,
        }

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
