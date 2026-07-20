import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from backend import server


# =====================================================
# get_rooms_data()
# =====================================================


@patch("backend.server.execute")
def test_get_rooms_empty_database(mock_execute):

    mock_execute.return_value = []


    result = server.get_rooms_data()


    assert result == []



@patch("backend.server.execute")
def test_get_rooms_one_room(mock_execute):

    mock_execute.return_value = [
        {
            "id":1,
            "name":"room1"
        }
    ]


    result = server.get_rooms_data()


    assert len(result) == 1



@patch("backend.server.execute")
def test_get_rooms_multiple_rooms(mock_execute):

    mock_execute.return_value = [
        {"id":1},
        {"id":2}
    ]


    result = server.get_rooms_data()


    assert len(result) == 2



@patch("backend.server.execute")
def test_get_rooms_date_format(mock_execute):

    mock_execute.return_value = [
        {
            "created_at": datetime(2026, 1, 1, 10, 0, 0)
        }
    ]

    result = server.get_rooms_data()

    assert result[0]["created_at"] == "2026-01-01 10:00:00"



@patch("backend.server.execute")
def test_get_rooms_sql_exception(mock_execute):

    mock_execute.side_effect = Exception(
        "SQL error"
    )


    with pytest.raises(Exception):

        server.get_rooms_data()



# =====================================================
# remove_player_from_room()
# =====================================================

@pytest.mark.asyncio
@patch("backend.server.broadcast_rooms", new_callable=AsyncMock)
@patch("backend.server.execute")
async def test_remove_player(
    mock_execute,
    mock_broadcast
):

    server.rooms_state = {
        "room1":{
            "players":[
                {
                    "id":"1",
                    "name":"test"
                }
            ],
            "watchers":[]
        }
    }

    await server.remove_player_from_room(
        "1",        
        "room1"     
    )

    assert "room1" not in server.rooms_state


@pytest.mark.asyncio
@patch("backend.server.broadcast_room_update", new_callable=AsyncMock)
@patch("backend.server.broadcast_rooms", new_callable=AsyncMock)
@patch("backend.server.execute")
async def test_remove_watcher(
    mock_execute,
    mock_rooms,
    mock_update
):

    server.rooms_state = {
        "room1":{
            "players":[
                {
                    "id":"2"
                }
            ],
            "watchers":[
                {
                    "id":"1"
                }
            ]
        }
    }

    await server.remove_player_from_room(
        "1",
        "room1"
    )

    assert len(server.rooms_state["room1"]["watchers"]) == 0



@pytest.mark.asyncio
@patch("backend.server.broadcast_room_update", new_callable=AsyncMock)
@patch("backend.server.execute")
async def test_remove_nonexistent_player(
    mock_execute,
    mock_update
):

    server.rooms_state = {
        "room1":{
            "players":[
                {
                    "id":"2"
                }
            ],
            "watchers":[]
        }
    }

    await server.remove_player_from_room(
        "100",
        "room1"
    )

    assert len(server.rooms_state["room1"]["players"]) == 1



@pytest.mark.asyncio
@patch("backend.server.broadcast_rooms", new_callable=AsyncMock)
@patch("backend.server.execute")
async def test_delete_empty_room(
    mock_execute,
    mock_rooms
):

    server.rooms_state = {
        "room1":{
            "players":[
                {
                    "id":"1"
                }
            ],
            "watchers":[]
        }
    }

    await server.remove_player_from_room(
        "1",
        "room1"
    )

    assert "room1" not in server.rooms_state



@pytest.mark.asyncio
@patch("backend.server.broadcast_room_update", new_callable=AsyncMock)
@patch("backend.server.execute")
async def test_keep_non_empty_room(
    mock_execute,
    mock_update
):

    server.rooms_state = {
        "room1":{
            "players":[
                {
                    "id":"1"
                },
                {
                    "id":"2"
                }
            ],
            "watchers":[]
        }
    }

    await server.remove_player_from_room(
        "1",
        "room1"
    )

    assert "room1" in server.rooms_state
    assert len(server.rooms_state["room1"]["players"]) == 1



@pytest.mark.asyncio
@patch("backend.server.broadcast_room_update", new_callable=AsyncMock)
@patch("backend.server.execute")
async def test_database_update_called(
    mock_execute,
    mock_update
):

    server.rooms_state = {
        "room1":{
            "players":[
                {
                    "id":"1"
                },
                {
                    "id":"2"
                }
            ],
            "watchers":[]
        }
    }

    await server.remove_player_from_room(
        "1",
        "room1"
    )

    assert mock_execute.called



# =====================================================
# close_room()
# =====================================================


@pytest.mark.asyncio
@patch(
    "backend.server.broadcast_rooms",
    new_callable=AsyncMock
)
@patch(
    "backend.server.execute"
)
async def test_close_room_host_disconnect(
    mock_execute,
    mock_broadcast
):

    server.rooms_state = {
        "room1":{
            "players":[
                {
                    "id":"1",
                    "name":"Alice"
                }
            ],
            "watchers":[]
        }
    }


    await server.close_room(
        "room1"
    )


    assert mock_execute.call_count == 2

    mock_broadcast.assert_called_once()

    assert "room1" not in server.rooms_state



@pytest.mark.asyncio
@patch(
    "backend.server.broadcast_rooms",
    new_callable=AsyncMock
)
async def test_close_room_clear_state(
    mock_broadcast
):

    server.rooms_state = {
        "room1":{
            "players":[],
            "watchers":[]
        }
    }


    await server.close_room(
        "room1"
    )


    assert "room1" not in server.rooms_state



@pytest.mark.asyncio
async def test_close_room_missing_room():

    server.rooms_state={}


    result = await server.close_room(
        "unknown"
    )


    assert result is None

@pytest.mark.asyncio
@patch(
    "backend.server.broadcast_rooms",
    new_callable=AsyncMock
)
async def test_close_room_notify_player(
    mock_broadcast
):

    ws = AsyncMock()


    server.connected_clients={
        "1":ws
    }


    server.rooms_state={
        "room1":{
            "players":[
                {
                    "id":"1"
                }
            ],
            "watchers":[]
        }
    }


    await server.close_room(
        "room1"
    )


    ws.send_text.assert_called_once()

    message = ws.send_text.call_args[0][0]

    assert "room_closed" in message