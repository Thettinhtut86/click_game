import re
from datetime import datetime

from click_game.repositories.chat_repository import ChatRepository
from click_game.repositories.player_repository import PlayerRepository

MENTION_REGEX = r"@([a-zA-Z0-9_]+)"
MAX_MESSAGE_LENGTH = 300


class ChatService:
    def __init__(
        self,
        chat: ChatRepository | None = None,
        players: PlayerRepository | None = None,
    ):
        self.chat = chat or ChatRepository()
        self.players = players or PlayerRepository()

    def send(self, user_id: str, name: str, text: str, connected_ids: list[str]) -> dict | None:
        text = text.strip()

        if not text or len(text) > MAX_MESSAGE_LENGTH:
            return None

        player = self.players.get(user_id)
        color = player.get("color") if player else "#ffffff"

        message_id = self.chat.create(user_id, name, color, text)

        message = {
            "id": message_id,
            "uid": user_id,
            "name": name,
            "color": color,
            "text": text,
            "timestamp": datetime.now().strftime("%H:%M"),
            "mentions": re.findall(MENTION_REGEX, text),
            "deleted": 0,
        }

        for connected_id in connected_ids:
            if connected_id != str(user_id):
                self.chat.increment_unread(connected_id)

        return message

    def history(self) -> list[dict]:
        messages = []

        for row in self.chat.history_today():
            created = row["created_at"]

            if isinstance(created, str):
                time_str = created[11:16]
            else:
                time_str = created.strftime("%H:%M")

            messages.append(
                {
                    "id": row["id"],
                    "uid": row["player_id"],
                    "name": row["player_name"],
                    "color": row["player_color"],
                    "text": row["message"],
                    "deleted": row.get("deleted", 0),
                    "timestamp": time_str,
                }
            )

        return messages

    def delete(self, user_id: str, message_id: int) -> bool:
        row = self.chat.get_owner(message_id)
        if not row or str(row["player_id"]) != str(user_id):
            return False

        self.chat.set_deleted(message_id, True)
        return True

    def restore(self, user_id: str, message_id: int) -> bool:
        row = self.chat.get_owner(message_id)
        if not row or str(row["player_id"]) != str(user_id):
            return False

        self.chat.set_deleted(message_id, False)
        return True

    def mark_seen(self, user_id: str) -> None:
        self.chat.mark_seen(user_id)

    def cleanup(self) -> None:
        self.chat.cleanup()
