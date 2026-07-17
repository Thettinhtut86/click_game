import asyncio
import pytest
from unittest.mock import patch

from backend import server


@pytest.mark.asyncio
@patch("backend.server.broadcast_to_all")
@patch("backend.server.execute")
async def test_run_daily_cleanup(
    mock_execute,
    mock_broadcast,
):
    await server.run_daily_cleanup()

    assert mock_execute.call_count == 4
    mock_broadcast.assert_called_once()


@patch("backend.server.asyncio.create_task")
@patch("backend.server.execute")
def test_startup_empty_db(
    mock_execute,
    mock_task,
):

    mock_execute.return_value = []

    server.rooms_state.clear()

    server.startup()

    mock_task.assert_called_once()
    assert server.rooms_state == {}


@patch("backend.server.asyncio.create_task")
@patch("backend.server.execute")
def test_startup_load_room(
    mock_execute,
    mock_task,
):

    mock_execute.side_effect = [
        [
            {
                "id": 1,
                "host_id": 10,
                "started": False
            }
        ],
        [
            {
                "id": 10,
                "name": "Alice",
                "room_id": 1,
                "joined_at": None,
                "color": "red"
            }
        ]
    ]

    server.rooms_state.clear()

    server.startup()

    assert "1" in server.rooms_state

    room = server.rooms_state["1"]

    assert room["host"] == "10"
    assert room["players"][0]["name"] == "Alice"


@patch("backend.server.asyncio.create_task")
@patch("backend.server.execute")
def test_startup_db_exception(
    mock_execute,
    mock_task,
):

    mock_execute.side_effect = Exception("DB failed")

    server.rooms_state.clear()

    # Should not raise
    server.startup()

    assert server.rooms_state == {}    