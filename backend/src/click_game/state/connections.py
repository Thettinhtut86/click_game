from fastapi import WebSocket


class ConnectionStore:
    def __init__(self):
        self.connections: dict[str, WebSocket] = {}

    def get(self, user_id: str) -> WebSocket | None:
        return self.connections.get(str(user_id))

    def add(self, user_id: str, websocket: WebSocket) -> None:
        self.connections[str(user_id)] = websocket

    def remove_if_same(self, user_id: str, websocket: WebSocket) -> None:
        if self.get(user_id) is websocket:
            self.connections.pop(str(user_id), None)

    def disconnect_by_id(self, user_id: str) -> None:
        self.connections.pop(str(user_id), None)

    def ids(self) -> list[str]:
        return list(self.connections.keys())

    def all(self):
        return self.connections.items()


connection_store = ConnectionStore()
