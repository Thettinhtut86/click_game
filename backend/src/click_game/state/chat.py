from datetime import datetime


class ChatState:
    def __init__(self):
        self.typing_users: dict[str, datetime] = {}

    def start_typing(self, user_id: str) -> None:
        self.typing_users[str(user_id)] = datetime.now()

    def stop_typing(self, user_id: str) -> None:
        self.typing_users.pop(str(user_id), None)


chat_state = ChatState()
