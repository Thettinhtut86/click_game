import logging

from fastapi import APIRouter, HTTPException

from click_game.services.room_service import RoomService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["rooms"])
service = RoomService()


@router.get("/rooms")
def list_rooms():
    try:
        return service.list_rooms()
    except Exception as exc:
        logger.exception("Failed to list rooms")
        raise HTTPException(status_code=500, detail="db error") from exc
