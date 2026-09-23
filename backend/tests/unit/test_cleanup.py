from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from click_game.services import cleanup_service


@pytest.mark.asyncio
async def test_run_daily_cleanup(monkeypatch):
    chat_cleanup_called = False
    execute_calls = []
    clear_called = False
    broadcast_calls = []

    class FakeChatService:
        def cleanup(self):
            nonlocal chat_cleanup_called
            chat_cleanup_called = True

    def fake_execute(query, params=None, fetch=None, dictionary=None, commit=False):
        execute_calls.append(
            {
                "query": query,
                "params": params,
                "fetch": fetch,
                "dictionary": dictionary,
                "commit": commit,
            }
        )

    def fake_clear():
        nonlocal clear_called
        clear_called = True

    async def fake_broadcast(message):
        broadcast_calls.append(message)

    monkeypatch.setattr(
        cleanup_service,
        "ChatService",
        FakeChatService,
    )

    monkeypatch.setattr(
        cleanup_service,
        "execute",
        fake_execute,
    )
    monkeypatch.setattr(
        cleanup_service.room_store,
        "clear",
        fake_clear,
    )
    monkeypatch.setattr(
        cleanup_service.websocket_manager,
        "broadcast",
        fake_broadcast,
    )

    await cleanup_service.run_daily_cleanup()
    
    assert chat_cleanup_called is True
    assert execute_calls == [
        {
            "query": "DELETE FROM players WHERE created_at < CURDATE()",
            "params": None,
            "fetch": False,
            "dictionary": False,
            "commit": True,
        }
    ]
    assert clear_called is True
    assert broadcast_calls == [{"action": "chat_reset"}]
