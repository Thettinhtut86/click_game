from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    user_name: str = Field(min_length=1, max_length=100)


class LogoutRequest(BaseModel):
    user_id: str | None = None
    player_id: str | None = None


class LoginResponse(BaseModel):
    status: str
    user_id: str
    userName: str
    color: str
    token: str
