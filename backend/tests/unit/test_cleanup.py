from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from click_game.services import cleanup_service
from click_game.state.rooms import room_store


@pytest.fixture(autouse=True)
def clean_rooms():
    room_store.clear()
    yield
    room_store.clear()


@pytest.mark.asyncio
async def test_run_daily_cleanup():
    chat = MagicMock()
    room_store.set("1", {})
    with patch.object(cleanup_service, "ChatService", return_value=chat), \
         patch.object(cleanup_service, "execute") as execute, \
         patch.object(cleanup_service.websocket_manager, "broadcast", new_callable=AsyncMock) as broadcast:
        await cleanup_service.run_daily_cleanup()

    chat.cleanup.assert_called_once()
    execute.assert_called_once_with(
        "DELETE FROM players WHERE created_at < CURDATE()",
        commit=True,
    )
    assert room_store.get("1") is None
    broadcast.assert_awaited_once_with({"action": "chat_reset"})


@pytest.mark.asyncio
async def test_daily_cleanup_loop_swallows_cleanup_exception():
    with patch.object(cleanup_service, "run_daily_cleanup", new_callable=AsyncMock, side_effect=RuntimeError("DB")), \
         patch.object(cleanup_service.asyncio, "sleep", new_callable=AsyncMock, side_effect=KeyboardInterrupt):
        with pytest.raises(KeyboardInterrupt):
            await cleanup_service.daily_cleanup_loop()
