import asyncio
from datetime import datetime, timedelta

from click_game.services.chat_service import ChatService
from click_game.state.rooms import room_store
from click_game.websocket.manager import websocket_manager
from click_game.db.database import execute


async def run_daily_cleanup():
    ChatService().cleanup()

    execute("DELETE FROM players WHERE joined_at < CURDATE()", commit=True)

    room_store.clear()

    await websocket_manager.broadcast({"action": "chat_reset"})


async def daily_cleanup_loop():
    while True:
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        next_midnight = tomorrow.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        wait_seconds = (next_midnight - now).total_seconds()

        await asyncio.sleep(wait_seconds)

        try:
            await run_daily_cleanup()
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Daily cleanup failed")
