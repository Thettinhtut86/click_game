from fastapi import HTTPException

from click_game.core.security import verify_token


def authenticate_token(token: str) -> dict:
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload
