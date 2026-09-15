import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException

from click_game.core.security import create_access_token
from click_game.repositories.player_repository import PlayerRepository
from click_game.schemas.auth import LoginRequest, LoginResponse, LogoutRequest
from click_game.services.auth_service import AuthService
from click_game.services.room_service import RoomService
from click_game.state.connections import connection_manager
from click_game.state.rooms import room_store
from click_game.websocket.manager import WebSocketManager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])

auth_service = AuthService(PlayerRepository())
room_service = RoomService(PlayerRepository())


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    try:
        player = auth_service.login(payload.user_name)
        token = create_access_token(
            {
                "user_id": str(player["id"]),
                "userName": player["name"],
                "color": player["color"],
            }
        )

        return LoginResponse(
            status="ok",
            user_id=str(player["id"]),
            userName=player["name"],
            color=player["color"],
            token=token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Login failed")
        raise HTTPException(status_code=500, detail="db error") from exc


@router.post("/logout")
def logout(background_tasks: BackgroundTasks, payload: LogoutRequest):
    uid = payload.user_id or payload.player_id

    if not uid or uid == "undefined":
        raise HTTPException(status_code=400, detail="user_id required")

    try:
        room_service.logout(uid)
        connection_manager.disconnect_by_id(uid)
        background_tasks.add_task(room_store.broadcast_rooms)
        return {"status": "logged_out", "userId": uid}
    except Exception as exc:
        logger.exception("Logout failed")
        raise HTTPException(status_code=500, detail="db error") from exc
