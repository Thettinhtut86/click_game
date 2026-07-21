import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from backend import server


# =====================================================
# Mock websocket
# =====================================================

@pytest.fixture
def mock_ws():
    ws = AsyncMock()
    ws.send_text = AsyncMock()
    return ws



# =====================================================
# handshake
# =====================================================

@pytest.mark.asyncio
@patch("backend.server.broadcast_online_users", new_callable=AsyncMock)
@patch("backend.server.mark_seen", new_callable=AsyncMock)
@patch("backend.server.broadcast_rooms", new_callable=AsyncMock)
async def test_handle_handshake(
        mock_broadcast_rooms,
        mock_mark_seen,
        mock_broadcast_online,
        mock_ws
):

    await server.handle_handshake(
        mock_ws,
        "1",
        "Alice"
    )

    mock_ws.send_text.assert_called_once()

    message = json.loads(
        mock_ws.send_text.call_args[0][0]
    )

    assert message["action"] == "handshake_ack"
    assert message["userId"] == "1"


    mock_broadcast_online.assert_called_once()

    mock_mark_seen.assert_called_once_with(
        "1"
    )

    mock_broadcast_rooms.assert_called_once()

# =====================================================
# create room
# =====================================================

@pytest.mark.asyncio
@patch("backend.server.broadcast_room_update", new_callable=AsyncMock)
@patch("backend.server.ensure_room")
@patch("backend.server.execute")
async def test_create_room_success(
    mock_execute,
    mock_ensure,
    mock_broadcast,
    mock_ws
):

    mock_execute.side_effect = [
        10,                 # insert room
        None,               # update player
        [{"color":"red"}]   # select player
    ]

    mock_ensure.side_effect=lambda x:x


    await server.handle_create_room(
        mock_ws,
        "1",
        "Alice",
        {
            "option":"asc"
        }
    )


    assert "10" in server.rooms_state

    mock_ws.send_text.assert_called()



@pytest.mark.asyncio
@patch(
    "backend.server.execute",
    side_effect=Exception("DB error")
)
async def test_create_room_db_error(
    mock_execute,
    mock_ws
):

    await server.handle_create_room(
        mock_ws,
        "1",
        "Alice",
        {}
    )


    message=json.loads(
        mock_ws.send_text.call_args[0][0]
    )

    assert message["action"]=="error"



# =====================================================
# join room
# =====================================================


@pytest.mark.asyncio
@patch(
    "backend.server.broadcast_rooms",
    new_callable=AsyncMock
)
@patch(
    "backend.server.broadcast_room_update",
    new_callable=AsyncMock
)
async def test_join_existing_room(
    mock_room_update,
    mock_rooms,
    mock_ws
):

    server.rooms_state={
        "1":{
            "host":"1",
            "players":[],
            "watchers":[],
            "game_started":False
        }
    }


    with patch(
        "backend.server.execute"
    ) as mock_execute:

        mock_execute.side_effect=[
            None,
            [{"color":"blue"}]
        ]

        await server.handle_join_room(
            mock_ws,
            "2",
            "Bob",
            {
                "roomId":"1"
            }
        )


    assert len(
        server.rooms_state["1"]["players"]
    ) == 1

    mock_room_update.assert_called_once()
    mock_rooms.assert_called_once()



@pytest.mark.asyncio
async def test_join_missing_room(mock_ws):

    server.rooms_state={}


    with patch(
        "backend.server.execute",
        return_value=None
    ):

        await server.handle_join_room(
            mock_ws,
            "1",
            "Alice",
            {
                "roomId":"999"
            }
        )


    msg=json.loads(
        mock_ws.send_text.call_args[0][0]
    )


    assert msg["message"]=="Room not found"



@pytest.mark.asyncio
async def test_join_game_started(mock_ws):

    server.rooms_state={
        "1":{
            "game_started":True
        }
    }


    await server.handle_join_room(
        mock_ws,
        "2",
        "Bob",
        {
            "roomId":"1"
        }
    )


    msg=json.loads(
        mock_ws.send_text.call_args[0][0]
    )


    assert msg["message"]=="Game already started"



@pytest.mark.asyncio
async def test_join_duplicate_player(mock_ws):

    server.rooms_state={
        "1":{
            "game_started":False,
            "players":[
                {
                    "id":"2"
                }
            ]
        }
    }


    await server.handle_join_room(
        mock_ws,
        "2",
        "Bob",
        {
            "roomId":"1"
        }
    )


    msg=json.loads(
        mock_ws.send_text.call_args[0][0]
    )


    assert msg["action"]=="join_ack"



# =====================================================
# leave room
# =====================================================


@pytest.mark.asyncio
async def test_leave_room_success(mock_ws):

    server.rooms_state={
        "1":{
            "game_started":False
        }
    }

    with patch(
        "backend.server.remove_player_from_room",
        new_callable=AsyncMock
    ) as mock_remove, patch(
        "backend.server.broadcast_rooms",
        new_callable=AsyncMock
    ) as mock_broadcast:

        await server.handle_leave_room(
            mock_ws,
            "1",
            {
                "roomId":"1"
            }
        )


    mock_remove.assert_awaited_once_with("1", "1")
    mock_ws.send_text.assert_called_once()
    mock_broadcast.assert_awaited_once()



@pytest.mark.asyncio
async def test_leave_running_game_rejected(mock_ws):

    server.rooms_state = {
        "1": {
            "game_started": True
        }
    }

    await server.handle_leave_room(
        mock_ws,
        "1",
        {
            "roomId": "1"
        }
    )

    mock_ws.send_text.assert_called_once()
    message = mock_ws.send_text.call_args.args[0]
    assert "Cannot leave room while game is active" in message


# =====================================================
# quit room
# =====================================================


@pytest.mark.asyncio
async def test_host_quit(mock_ws):

    server.rooms_state={
        "1":{
            "host":"1"
        }
    }


    with patch(
        "backend.server.close_room",
        new_callable=AsyncMock
    ) as mock_close:


        await server.handle_quit_room(
            mock_ws,
            "1",
            {
                "roomId":"1"
            }
        )


    mock_close.assert_called_once_with("1")



@pytest.mark.asyncio
async def test_player_quit(mock_ws):

    server.rooms_state={
        "1":{
            "host":"1"
        }
    }

    with patch(
        "backend.server.remove_player_from_room",
        new_callable=AsyncMock
    ) as mock_remove, patch(
        "backend.server.broadcast_rooms",
        new_callable=AsyncMock
    ) as mock_broadcast:

        await server.handle_quit_room(
            mock_ws,
            "2",
            {
                "roomId": "1"
            }
        )

    mock_remove.assert_awaited_once_with("2", "1")
    mock_broadcast.assert_awaited_once()

    mock_ws.send_text.assert_awaited_once_with(
        json.dumps({
            "action": "quit_ack",
            "roomId": "1"
        })
    )



# =====================================================
# typing
# =====================================================


@pytest.mark.asyncio
@patch(
    "backend.server.broadcast_typing",
    new_callable=AsyncMock
)
async def test_typing_start(mock_broadcast):

    await server.handle_typing_start(
        "1",
        "Alice"
    )


    mock_broadcast.assert_called_once()



@pytest.mark.asyncio
@patch(
    "backend.server.broadcast_typing",
    new_callable=AsyncMock
)
async def test_typing_stop(mock_broadcast):

    await server.handle_typing_stop(
        "1",
        "Alice"
    )


    mock_broadcast.assert_called_once()



# =====================================================
# get rooms
# =====================================================


@pytest.mark.asyncio
async def test_get_rooms(mock_ws):

    with patch(
        "backend.server.get_rooms_data",
        return_value=[]
    ):


        await server.handle_get_rooms(
            mock_ws,
            "1",
            "Alice",
            {}
        )


    msg=json.loads(
        mock_ws.send_text.call_args[0][0]
    )


    assert msg["action"]=="rooms_update"



# =====================================================
# websocket router
# =====================================================


@pytest.mark.asyncio
async def test_unknown_action(mock_ws):

    await server.handle_ws_action(
        mock_ws,
        "1",
        "Alice",
        {
            "action":"UNKNOWN"
        }
    )


    msg=json.loads(
        mock_ws.send_text.call_args[0][0]
    )


    assert msg["action"]=="error"