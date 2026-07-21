import pytest
from unittest.mock import AsyncMock, patch

from backend import server


# =====================================================
# handle_send_message()
# =====================================================


@pytest.mark.asyncio
@patch("backend.server.broadcast_to_all", new_callable=AsyncMock)
@patch("backend.server.execute")
async def test_send_normal_message(
    mock_execute,
    mock_broadcast
):

    mock_execute.side_effect=[
        [{"color":"red"}],
        1,
        1
    ]

    result = await server.handle_send_message(
        None,
        "1001",
        "player1",
        {
            "text":"hello"
        }
    )

    assert result is None

    mock_broadcast.assert_called_once()


@pytest.mark.asyncio
@patch("backend.server.execute")
async def test_send_empty_messagem(mock_execute):

    await server.handle_send_message(
        None,
        "1001",
        "player1",
        {
            "text": ""
        }
    )

    mock_execute.assert_not_called()



@pytest.mark.asyncio
@patch("backend.server.execute")
async def test_send_too_long_message(mock_execute):

    await server.handle_send_message(
        None,
        "1001",
        "player1",
        {
            "text":"x"*301
        }
    )

    mock_execute.assert_not_called()



@pytest.mark.asyncio
@patch(
    "backend.server.broadcast_to_all",
    new_callable=AsyncMock
)
@patch("backend.server.execute")
async def test_mention_detection(
    mock_execute,
    mock_broadcast
):

    mock_execute.side_effect=[
        [{"color":"red"}],
        1,
        1
    ]


    await server.handle_send_message(
        None,
        "1001",
        "player1",
        {
            "text":"hello @user"
        }
    )


    assert mock_broadcast.call_count == 2



@pytest.mark.asyncio
@patch("backend.server.broadcast_to_all")
@patch("backend.server.execute")
async def test_multiple_mentions(mock_execute, mock_broadcast):

    mock_execute.side_effect = [
        [{"color": "red"}],
        1,
        1
    ]

    await server.handle_send_message(
        None,
        "1001",
        "player1",
        {
            "text": "@user1 @user2 hello"
        }
    )

    assert mock_broadcast.call_count >= 3


@pytest.mark.asyncio
@patch("backend.server.broadcast_to_all", new_callable=AsyncMock)
@patch("backend.server.execute")
async def test_send_message_without_player_color(
    mock_execute,
    mock_broadcast
):

    mock_execute.side_effect=[
        [],
        1,
        1
    ]


    await server.handle_send_message(
        None,
        "1001",
        "player1",
        {
            "text":"hello"
        }
    )


    message = mock_broadcast.call_args[0][0]

    assert message["message"]["color"]=="#ffffff"



@pytest.mark.asyncio
@patch("backend.server.execute")
@patch("backend.server.broadcast_to_all")
async def test_message_saved(mock_broadcast, mock_execute):

    mock_execute.side_effect = [
        [{"color": "red"}],
        1,
        1
    ]

    await server.handle_send_message(
        None,
        "1001",
        "player1",
        {
            "text": "hello"
        }
    )

    assert mock_execute.called



@pytest.mark.asyncio
@patch("backend.server.broadcast_to_all")
@patch("backend.server.execute")
async def test_message_broadcast(mock_execute, mock_broadcast):

    mock_execute.side_effect = [
        [{"color": "red"}],
        1,
        1
    ]

    await server.handle_send_message(
        None,
        "1001",
        "player1",
        {
            "text": "hello"
        }
    )

    mock_broadcast.assert_called()



@pytest.mark.asyncio
@patch("backend.server.execute")
@patch("backend.server.broadcast_to_all")
async def test_unread_increment(mock_broadcast, mock_execute):

    server.connected_clients = {
        "2001": None
    }

    mock_execute.side_effect = [
        [{"color": "red"}],  # SELECT color
        1,                   # INSERT daily_chat
        1                    # INSERT chat_unread
    ]

    await server.handle_send_message(
        None,
        "1001",
        "player1",
        {
            "text": "hello"
        }
    )

    assert mock_execute.call_count == 3



# =====================================================
# handle_delete_message()
# =====================================================


@pytest.mark.asyncio
@patch("backend.server.broadcast_to_all")
@patch("backend.server.execute")
async def test_delete_owner_message(mock_execute, mock_broadcast):

    mock_execute.side_effect = [
        [
            {
                "player_id": "1001"
            }
        ],
        1
    ]

    result = await server.handle_delete_message(
        "1001",
        {
            "message_id": 1
        }
    )

    assert result is None
    mock_broadcast.assert_called_once()



@pytest.mark.asyncio
@patch("backend.server.execute")
async def test_delete_not_owner(mock_execute):

    mock_execute.return_value = [
        {
            "player_id": "2000"
        }
    ]

    result = await server.handle_delete_message(
        "1001",
        {
            "message_id": 1
        }
    )

    assert result is None



@pytest.mark.asyncio
async def test_delete_missing_id():

    result = await server.handle_delete_message(
        "1001",
        {}
    )

    assert result is None



@pytest.mark.asyncio
@patch("backend.server.execute")
async def test_delete_unknown_id(mock_execute):

    mock_execute.return_value = []

    result = await server.handle_delete_message(
        "1001",
        {
            "message_id": 99999
        }
    )

    assert result is None



@pytest.mark.asyncio
@patch("backend.server.broadcast_to_all")
@patch("backend.server.execute")
async def test_delete_broadcast(mock_execute, mock_broadcast):

    mock_execute.side_effect = [
        [
            {
                "player_id": "1001"
            }
        ],
        1
    ]

    await server.handle_delete_message(
        "1001",
        {
            "message_id": 1
        }
    )

    mock_broadcast.assert_called_once()



# =====================================================
# handle_restore_message()
# =====================================================


@pytest.mark.asyncio
@patch("backend.server.broadcast_to_all")
@patch("backend.server.execute")
async def test_restore_owner_message(mock_execute, mock_broadcast):

    mock_execute.side_effect = [
        [
            {
                "player_id": "1001"
            }
        ],
        1
    ]

    result = await server.handle_restore_message(
        "1001",
        {
            "message_id": 1
        }
    )

    assert result is None
    mock_broadcast.assert_called_once()



@pytest.mark.asyncio
async def test_restore_missing_id():

    result = await server.handle_restore_message(
        "1001",
        {}
    )

    assert result is None



@pytest.mark.asyncio
@patch("backend.server.execute")
async def test_restore_not_owner(mock_execute):

    mock_execute.return_value = [
        {
            "player_id": "2000"
        }
    ]

    result = await server.handle_restore_message(
        "1001",
        {
            "message_id": 1
        }
    )

    assert result is None



# =====================================================
# mark_seen()
# =====================================================

@pytest.mark.asyncio
@patch("backend.server.execute")
@patch("backend.server.fetch_one")
async def test_mark_seen_last_message(
        mock_fetch_one,
        mock_execute
):

    mock_fetch_one.return_value = {
        "last_id":10
    }


    mock_execute.return_value = 1


    result = await server.mark_seen(
        "1001"
    )


    assert result is None


    mock_fetch_one.assert_called_once()


    mock_execute.assert_called_once_with(
        """
        UPDATE chat_unread
        SET last_seen=%s
        WHERE user_id=%s
        """,
        (
            10,
            "1001"
        ),
        commit=True
    )


@pytest.mark.asyncio
@patch("backend.server.execute")
async def test_mark_seen_no_messages(mock_execute):

    mock_execute.side_effect = [
        [
            {
                "last_id": None
            }
        ],
        1,
        1
    ]

    result = await server.mark_seen(
        "1001"
    )

    assert result is None



@pytest.mark.asyncio
@patch("backend.server.execute")
async def test_reset_unread(mock_execute):

    mock_execute.side_effect = [
        [
            {
                "last_id": 5
            }
        ],
        1,
        1
    ]

    await server.mark_seen(
        "1001"
    )

    assert mock_execute.called



@pytest.mark.asyncio
@patch("backend.server.execute")
async def test_insert_chat_reads(mock_execute):

    mock_execute.side_effect = [
        [
            {
                "last_id": 5
            }
        ],
        1,
        1
    ]

    await server.mark_seen(
        "1001"
    )

    assert mock_execute.call_count >= 2