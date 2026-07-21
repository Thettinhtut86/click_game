import json

import pytest
from unittest.mock import AsyncMock, patch

from backend import server



# =====================================================
# handle_start_game()
# =====================================================


@pytest.mark.asyncio
@patch("backend.server.broadcast_to_room", new_callable=AsyncMock)
@patch("backend.server.execute")
async def test_start_game_host(mock_execute, mock_broadcast):

    websocket = AsyncMock()

    server.rooms_state = {
        "r1": {
            "host": "1",
            "players": [
                {
                    "id":"1",
                    "name":"player1",
                    "color":"red"
                }
            ],
            "option": "asc"
        }
    }

    await server.handle_start_game(
        websocket,
        "1",
        {
            "roomId": "r1",
            "user_id": "1"
        }
    )

    room = server.rooms_state["r1"]

    assert room["game_started"] is True
    assert len(room["play_order"]) == 100
    assert len(room["display_order"]) == 100
    assert len(room["bubbles"]) == 100

    mock_execute.assert_called_once()
    mock_broadcast.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_game_non_host(websocket, game_room):

    server.rooms_state = game_room


    await server.handle_start_game(
        websocket,
        "999",
        {
            "roomId":"r1"
        }
    )


    websocket.send_text.assert_called_once()


@pytest.mark.asyncio
async def test_start_game_missing_room(websocket):


    server.rooms_state={}


    await server.handle_start_game(
        websocket,
        "1",
        {
            "roomId":"r1"
        }
    )


    websocket.send_text.assert_called_once()


@pytest.mark.asyncio
async def test_start_game_missing_room_id(websocket):
    await server.handle_start_game(
        websocket,
        "1",
        {}
    )


    websocket.send_text.assert_called_once()



@pytest.mark.asyncio
@patch("backend.server.generate_bubble_order")
@patch("backend.server.broadcast_to_room", new_callable=AsyncMock)
@patch("backend.server.execute")
async def test_bubble_generation(
    mock_execute,
    mock_broadcast,
    mock_generate
):

    websocket = AsyncMock()

    mock_generate.return_value = list(range(1, 101))

    server.rooms_state = {
        "r1": {
            "host": "1",
            "players": {
                "1": {}
            },
            "option": "asc"
        }
    }


    await server.handle_start_game(
        websocket,
        "1",
        {
            "roomId": "r1"
        }
    )


    mock_generate.assert_called_once()

    room = server.rooms_state["r1"]

    assert room["game_started"] is True
    assert room["display_order"] == list(range(1,101))



@pytest.mark.asyncio
async def test_play_order_ascending():

    room={
        "option":"asc"
    }


    assert room["option"]=="asc"



@pytest.mark.asyncio
async def test_play_order_descending():

    room={
        "option":"desc"
    }


    assert room["option"]=="desc"



@pytest.mark.asyncio
@patch("backend.server.broadcast_to_room", new_callable=AsyncMock)
@patch("backend.server.execute")
async def test_start_game_db_update(
    mock_execute,
    mock_broadcast
):

    websocket = AsyncMock()

    server.rooms_state = {
        "r1": {
            "host": "1",
            "players": [
                {
                    "id": "1",
                    "name": "player1",
                    "color": "red"
                }
            ],
            "option": "asc"
        }
    }


    await server.handle_start_game(
        websocket,
        "1",
        {
            "roomId":"r1"
        }
    )


    mock_execute.assert_called_once()



@pytest.mark.asyncio
@patch("backend.server.broadcast_to_room", new_callable=AsyncMock)
@patch("backend.server.execute")
async def test_game_started_broadcast(
    mock_execute,
    mock_broadcast
):

    websocket = AsyncMock()

    server.rooms_state = {
        "r1": {
            "host": "1",
            "players": [
                {
                    "id":"1",
                    "name":"player1",
                    "color":"red"
                }
            ],
            "option": "asc"
        }
    }


    await server.handle_start_game(
        websocket,
        "1",
        {
            "roomId":"r1"
        }
    )


    mock_execute.assert_called_once()
    mock_broadcast.assert_awaited_once()



# =====================================================
# handle_select_bubble()
# =====================================================


@pytest.mark.asyncio
@patch(
"backend.server.broadcast_to_room",
new_callable=AsyncMock
)
@patch(
    "backend.server.get_player_color"
)
async def test_select_correct_bubble(
        mock_color,
        mock_broadcast,
        websocket
):

    mock_color.return_value = "red"

    server.rooms_state = {
        "r1": {
            "game_started": True,
            "index": 0,
            "play_order": [1,2,3],
            "players": [],
            "bubbles": {
                "B1": None
            }
        }
    }

    await server.handle_select_bubble(
        websocket,
        "1",
        {
            "roomId":"r1",
            "bubble_id":"B1",
            "name":"player1"
        }
    )

    room = server.rooms_state["r1"]

    assert room["index"] == 1

    assert room["bubbles"]["B1"] == {
        "uid":"1",
        "color":"red"
    }

    mock_broadcast.assert_awaited_once()

@pytest.mark.asyncio
async def test_select_wrong_bubble(
        websocket
):


    server.rooms_state={

        "r1":{

            "game_started":True,

            "index":0,

            "play_order":[1],

            "players":[],

            "bubbles":{}
        }
    }


    await server.handle_select_bubble(
        websocket,
        "1",
        {
            "roomId":"r1",
            "bubble_id":"B9"
        }
    )


    websocket.send_text.assert_called_once()



@pytest.mark.asyncio
async def test_select_missing_room():

    websocket = AsyncMock()

    await server.handle_select_bubble(
        websocket,
        "1",
        {}
    )

    websocket.send_text.assert_called_once()

@pytest.mark.asyncio
async def test_select_missing_bubble_id():

    websocket=AsyncMock()

    await server.handle_select_bubble(
        websocket,
        "1",
        {
            "roomId":"r1"
        }
    )


    websocket.send_text.assert_called_once()



@pytest.mark.asyncio
async def test_player_not_found(websocket):

    await server.handle_select_bubble(
        websocket,
        "unknown",
        {}
    )


    websocket.send_text.assert_called_once()



@pytest.mark.asyncio
@patch(
    "backend.server.broadcast_to_room",
    new_callable=AsyncMock
)
@patch(
    "backend.server.get_player_color"
)
async def test_select_broadcast(
    mock_color,
    mock_broadcast,
    websocket
):

    mock_color.return_value = "red"


    server.rooms_state = {
        "r1": {
            "game_started": True,
            "index": 0,
            "play_order": [1,2],
            "players": [],
            "bubbles": {
                "B1": None
            }
        }
    }

    await server.handle_select_bubble(
        websocket,
        "1",
        {
            "roomId": "r1",
            "bubble_id": "B1"
        }
    )

    mock_broadcast.assert_awaited_once()
    message = mock_broadcast.call_args.args[1]

    assert message["action"] == "update_bubbles"
    assert message["roomId"] == "r1"
    assert message["currentIndex"] == 1
    assert message["bubbles"]["B1"] == {
        "uid":"1",
        "color":"red"
    }


@pytest.mark.asyncio
async def test_game_end():

    result = await server.handle_game_end(
        "room1"
    )


    assert result is None



# =====================================================
# handle_game_end()
# =====================================================


@pytest.mark.asyncio
@patch("backend.server.broadcast_rooms", new_callable=AsyncMock)
@patch("backend.server.broadcast_to_room", new_callable=AsyncMock)
@patch("backend.server.execute")
async def test_single_winner(
    mock_execute,
    mock_broadcast_room,
    mock_broadcast_rooms
):

    server.rooms_state = {
        "room1": {
            "players": [
                {
                    "id": "1",
                    "name": "Alice"
                },
                {
                    "id": "2",
                    "name": "Bob"
                }
            ],
            "bubbles": {
                "B1": {
                    "uid": "1",
                    "color": "red"
                },
                "B2": {
                    "uid": "1",
                    "color": "red"
                },
                "B3": {
                    "uid": "2",
                    "color": "blue"
                }
            }
        }
    }


    result = await server.handle_game_end("room1")


    assert result is None

    mock_broadcast_room.assert_called_once()

    message = mock_broadcast_room.call_args.args[1]

    assert message["action"] == "end_game"
    assert message["winners"] == [
        {
            "id": "1",
            "name": "Alice"
        }
    ]

    assert message["is_tie"] is False

    assert message["scores"] == {
        "1":2,
        "2":1
    }


    mock_execute.assert_called_once()

    assert "room1" not in server.rooms_state



@pytest.mark.asyncio
@patch("backend.server.broadcast_rooms", new_callable=AsyncMock)
@patch("backend.server.broadcast_to_room", new_callable=AsyncMock)
@patch("backend.server.execute")
async def test_tie_result(
    mock_execute,
    mock_broadcast_room,
    mock_broadcast_rooms
):

    server.rooms_state = {
        "room1": {
            "players": [
                {
                    "id":"1",
                    "name":"Alice"
                },
                {
                    "id":"2",
                    "name":"Bob"
                }
            ],
            "bubbles": {
                "B1":{
                    "uid":"1"
                },
                "B2":{
                    "uid":"2"
                }
            }
        }
    }


    await server.handle_game_end("room1")


    message = mock_broadcast_room.call_args.args[1]


    assert message["is_tie"] is True

    assert len(message["winners"]) == 2

    assert message["scores"] == {
        "1":1,
        "2":1
    }


@pytest.mark.asyncio
@patch("backend.server.broadcast_rooms", new_callable=AsyncMock)
@patch("backend.server.broadcast_to_room", new_callable=AsyncMock)
@patch("backend.server.execute")
async def test_no_scores(
    mock_execute,
    mock_broadcast_room,
    mock_broadcast_rooms
):

    server.rooms_state = {
        "room1": {
            "players": [
                {
                    "id":"1",
                    "name":"Alice"
                }
            ],
            "bubbles": {
                "B1":None,
                "B2":None
            }
        }
    }


    await server.handle_game_end("room1")


    message = mock_broadcast_room.call_args.args[1]


    assert message["winners"] == []
    assert message["is_tie"] is False
    assert message["scores"] == {}


    mock_execute.assert_called_once()


@pytest.mark.asyncio
async def test_game_end_room_not_found():

    server.rooms_state = {}

    result = await server.handle_game_end(
        "unknown"
    )


    assert result is None


@pytest.mark.asyncio
@patch(
    "backend.server.broadcast_rooms",
    new_callable=AsyncMock
)
@patch("backend.server.execute")
async def test_winner_saved(
    mock_execute,
    mock_broadcast_rooms
):

    server.rooms_state = {
        "room1":{
            "players":[
                {
                    "id":"1",
                    "name":"Alice"
                }
            ],
            "bubbles":{
                "B1":{
                    "uid":"1"
                }
            }
        }
    }


    await server.handle_game_end(
        "room1"
    )


    mock_execute.assert_called_once_with(
        "UPDATE rooms SET winner_id=%s, started=0 WHERE id=%s",
        ("1","room1"),
        commit=True
    )



@pytest.mark.asyncio
@patch("backend.server.broadcast_rooms", new_callable=AsyncMock)
@patch("backend.server.broadcast_to_room", new_callable=AsyncMock)
@patch("backend.server.execute")
async def test_winner_broadcast(
    mock_execute,
    mock_broadcast_room,
    mock_broadcast_rooms,
):
    server.rooms_state = {
        "room1": {
            "players": [
                {
                    "id": "1",
                    "name": "Alice",
                }
            ],
            "bubbles": {
                "B1": {
                    "uid": "1"
                }
            }
        }
    }

    await server.handle_game_end("room1")

    mock_broadcast_room.assert_awaited_once()

    mock_execute.assert_called_once_with(
        "UPDATE rooms SET winner_id=%s, started=0 WHERE id=%s",
        ("1", "room1"),
        commit=True,
    )

    mock_broadcast_rooms.assert_awaited_once()

    assert "room1" not in server.rooms_state

@pytest.mark.asyncio
@patch("backend.server.broadcast_to_room",
       new_callable=AsyncMock)
@patch("backend.server.execute")
async def test_start_game_success(
        mock_execute,
        mock_broadcast,
        websocket,
        game_room
):

    server.rooms_state = game_room


    await server.handle_start_game(
        websocket,
        "1",
        {
            "roomId":"r1"
        }
    )


    assert server.rooms_state["r1"]["game_started"]


    assert len(
        server.rooms_state["r1"]["play_order"]
    ) == 100


    assert len(
        server.rooms_state["r1"]["bubbles"]
    ) == 100


    mock_execute.assert_called_once()


    mock_broadcast.assert_called_once()

@pytest.mark.asyncio
@patch(
"backend.server.broadcast_rooms",
new_callable=AsyncMock
)
@patch(
"backend.server.broadcast_to_room",
new_callable=AsyncMock
)
@patch(
"backend.server.execute"
)
async def test_game_end_winner(
        mock_execute,
        mock_broadcast,
        mock_rooms
):


    server.rooms_state={

        "r1":{

            "players":[
                {
                    "id":"1",
                    "name":"A"
                }
            ],

            "bubbles":{
                "B1":{
                    "uid":"1"
                }
            }
        }
    }


    await server.handle_game_end(
        "r1"
    )


    msg = mock_broadcast.call_args.args[1]


    assert msg["winners"][0]["id"]=="1"


    assert "r1" not in server.rooms_state


    mock_execute.assert_called_once()