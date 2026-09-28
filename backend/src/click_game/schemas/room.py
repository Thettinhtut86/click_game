from pydantic import BaseModel


class CreateRoomRequest(BaseModel):
    option: str = "asc"


class RoomSummary(BaseModel):
    id: int
    host_id: int | None = None
    host_name: str | None = None
    created_at: str | None = None
    player_count: int = 0
