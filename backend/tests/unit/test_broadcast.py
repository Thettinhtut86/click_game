import pytest
from unittest.mock import AsyncMock, patch

from backend import server



# =====================================================
# broadcast_to_all()
# =====================================================


@pytest.mark.asyncio
async def test_broadcast_one_client():

    ws = AsyncMock()

    server.connected_clients = {
        "1001": ws
    }


    await server.broadcast_to_all(
        {
            "type":"test"
        }
    )


    ws.send_text.assert_called_once()



@pytest.mark.asyncio
async def test_broadcast_multiple_clients():

    ws1 = AsyncMock()
    ws2 = AsyncMock()

    server.connected_clients = {
        "1001": ws1,
        "1002": ws2
    }


    await server.broadcast_to_all({})


    assert ws1.send_text.called
    assert ws2.send_text.called



@pytest.mark.asyncio
async def test_broadcast_disconnected_socket():

    ws = AsyncMock()

    ws.send_text.side_effect = Exception()


    server.connected_clients = {
        "1001": ws
    }


    await server.broadcast_to_all({})

    assert True



@pytest.mark.asyncio
async def test_broadcast_exception_ignored():

    ws=AsyncMock()

    ws.send_json.side_effect=Exception(
        "error"
    )

    server.clients=[ws]


    await server.broadcast_to_all({})



# =====================================================
# broadcast_to_room()
# =====================================================


@pytest.mark.asyncio
async def test_broadcast_players_only():

    ws = AsyncMock()

    server.connected_clients = {
        "1": ws
    }

    server.rooms_state = {
        "room1": {
            "players": [
                {
                    "id": "1"
                }
            ],
            "watchers": []
        }
    }


    await server.broadcast_to_room(
        "room1",
        {}
    )

    ws.send_text.assert_called_once()

@pytest.mark.asyncio
async def test_broadcast_watchers():

    ws = AsyncMock()

    server.connected_clients = {
        "1": ws
    }

    server.rooms_state = {
        "room1": {
            "players": [],
            "watchers": [
                {
                    "id": "1"
                }
            ]
        }
    }

    await server.broadcast_to_room(
        "room1",
        {}
    )

    ws.send_text.assert_called_once()

@pytest.mark.asyncio
async def test_missing_room():

    await server.broadcast_to_room(
        "unknown",
        {}
    )


@pytest.mark.asyncio
async def test_missing_websocket():

    server.rooms_state = {
        "room1": {
            "players": [
                {
                    "id": "1"
                }
            ],
            "watchers": []
        }
    }

    server.connected_clients = {}

    await server.broadcast_to_room(
    "room1",
    {}
)



# =====================================================
# broadcast_rooms()
# =====================================================


@pytest.mark.asyncio
@patch("backend.server.get_rooms_data")
async def test_broadcast_rooms(mock_rooms):

    mock_rooms.return_value=[]


    await server.broadcast_rooms()


    mock_rooms.assert_called()



@pytest.mark.asyncio
@patch("backend.server.get_rooms_data")
@patch("backend.server.broadcast_to_all")
async def test_send_room_update(mock_broadcast, mock_rooms):

    mock_rooms.return_value = []
    await server.broadcast_rooms()

    mock_rooms.assert_called()
    mock_broadcast.assert_called()



# =====================================================
# broadcast_room_update()
# =====================================================


@pytest.mark.asyncio
async def test_valid_room_update():

    await server.broadcast_room_update(
        "room1"
    )


    assert True



@pytest.mark.asyncio
async def test_invalid_room_update():

    await server.broadcast_room_update(
        "unknown"
    )

    assert True



# =====================================================
# chat broadcast
# =====================================================


@pytest.mark.asyncio
async def test_broadcast_chat_payload():

    ws=AsyncMock()

    server.connected_clients={
        "1001":ws
    }


    await server.broadcast_chat_message(
        {
            "message":"hello"
        }
    )


    ws.send_text.assert_called_once()



# =====================================================
# typing
# =====================================================


@pytest.mark.asyncio
async def test_typing_start():

    await server.broadcast_typing(
        "typing_start",
        "user1",
        "player1"
    )

    assert True



@pytest.mark.asyncio
async def test_typing_stop():

    await server.broadcast_typing(
        "typing_stop",
        "user1",
        "player1"
    )

    assert True



# =====================================================
# online users
# =====================================================


@pytest.mark.asyncio
@patch("backend.server.execute")
async def test_online_one_user(mock_execute):

    server.connected_clients = {
        "1": None
    }

    mock_execute.return_value = [
        {
            "id": "1",
            "name": "player1",
            "color": "red"
        }
    ]

    await server.broadcast_online_users()


@pytest.mark.asyncio
@patch("backend.server.execute")
async def test_online_multiple_users(mock_execute):

    server.clients={
        "user1":None,
        "user2":None
    }

    mock_execute.return_value = [
        {"id": "user1", "name": "player1", "color": "red"},
        {"id": "user2", "name": "player2", "color": "blue"}
    ]

    await server.broadcast_online_users()
    mock_execute.assert_called()


@pytest.mark.asyncio
@patch("backend.server.execute")
async def test_online_empty(mock_execute):

    server.clients=[]

    mock_execute.return_value = []

    await server.broadcast_online_users()
    mock_execute.assert_called()