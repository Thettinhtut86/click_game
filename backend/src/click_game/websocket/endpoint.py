import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from click_game.core.security import verify_token
from click_game.services.websocket_service import WebSocketService

logger = logging.getLogger(__name__)
router = APIRouter()
service = WebSocketService()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=1008)
        return

    payload = verify_token(token)

    if not payload or not payload.get("user_id") or not payload.get("userName"):
        await websocket.close(code=1008)
        return

    user_id = str(payload["user_id"])
    user_name = payload["userName"]

    await websocket.accept()
    service.connect(user_id, websocket)

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"error": "Invalid JSON format"})
                )
                continue

            await service.dispatch(
                websocket=websocket,
                user_id=user_id,
                user_name=user_name,
                data=message,
            )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: %s", user_id)
    except Exception:
        logger.exception("WebSocket crashed: %s", user_id)
    finally:
        await service.disconnect(user_id, user_name, websocket)
