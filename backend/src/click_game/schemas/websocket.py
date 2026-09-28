from pydantic import BaseModel, Field


class WSMessage(BaseModel):
    action: str = Field(min_length=1)
