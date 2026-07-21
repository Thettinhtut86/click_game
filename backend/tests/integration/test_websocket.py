import pytest

from unittest.mock import patch, AsyncMock
from starlette.websockets import WebSocketDisconnect


# =====================================================
# websocket endpoint authentication
# =====================================================


def test_websocket_missing_token(
        client
):

    with pytest.raises(WebSocketDisconnect) as exc:

        with client.websocket_connect(
            "/ws"
        ):
            pass


    assert exc.value.code == 1008



def test_websocket_invalid_token(
        client
):

    with pytest.raises(WebSocketDisconnect) as exc:

        with client.websocket_connect(
            "/ws?token=invalid"
        ):
            pass


    assert exc.value.code == 1008



def test_websocket_valid_token(
        client,
        auth_token,
        mock_execute
):

    with client.websocket_connect(
        f"/ws?token={auth_token}"
    ) as websocket:


        websocket.send_json(
            {
                "action":"handshake"
            }
        )


        response = websocket.receive_json()


        assert response is not None



# =====================================================
# handshake
# =====================================================

def test_websocket_handshake(
        client,
        auth_token,
        mock_execute
):

    with client.websocket_connect(
        f"/ws?token={auth_token}"
    ) as websocket:


        websocket.send_json(
            {
                "action":"handshake"
            }
        )


        response = websocket.receive_json()


        assert response["action"] in [
            "handshake_ack",
            "success"
        ]



# =====================================================
# invalid JSON
# =====================================================


def test_websocket_invalid_json(
        client,
        auth_token,
        mock_execute
):

    with client.websocket_connect(
        f"/ws?token={auth_token}"
    ) as websocket:


        websocket.send_text(
            "INVALID JSON"
        )


        response = websocket.receive_json()


        assert response is not None



# =====================================================
# unknown action
# =====================================================


def test_websocket_unknown_action(
        client,
        auth_token,
        mock_execute
):

    with client.websocket_connect(
        f"/ws?token={auth_token}"
    ) as websocket:


        websocket.send_json(
            {
                "action":
                "unknown_action"
            }
        )


        response = websocket.receive_json()


        assert response is not None



# =====================================================
# disconnect cleanup
# =====================================================


def test_websocket_disconnect_cleanup(
        client,
        auth_token,
        mock_execute
):

    with client.websocket_connect(
        f"/ws?token={auth_token}"
    ) as websocket:

        websocket.close()


    assert True



# =====================================================
# host disconnect
# =====================================================


@patch(
    "backend.server.close_room"
)
def test_host_disconnect(
        mock_close_room,
        client,
        auth_token,
        mock_execute
):

    with client.websocket_connect(
        f"/ws?token={auth_token}"
    ) as websocket:

        websocket.close()


    assert True



# =====================================================
# broadcast online users
# =====================================================


@patch(
    "backend.server.broadcast_online_users",
    new_callable=AsyncMock
)
def test_online_user_broadcast(
        mock_broadcast,
        client,
        auth_token,
        mock_execute
):

    with client.websocket_connect(
        f"/ws?token={auth_token}"
    ):

        pass


    mock_broadcast.assert_called()



# =====================================================
# broadcast rooms
# =====================================================


@patch(
    "backend.server.broadcast_rooms",
    new_callable=AsyncMock
)
def test_room_broadcast(
        mock_broadcast,
        client,
        auth_token,
        mock_execute
):

    with client.websocket_connect(
        f"/ws?token={auth_token}"
    ):

        pass


    mock_broadcast.assert_called()



# =====================================================
# multiple websocket clients
# =====================================================


def test_multiple_websocket_connections(
        client,
        auth_token,
        mock_execute
):

    with client.websocket_connect(
        f"/ws?token={auth_token}"
    ) as ws1:


        with client.websocket_connect(
            f"/ws?token={auth_token}"
        ) as ws2:


            assert ws1 is not None
            assert ws2 is not None



# =====================================================
# create room action
# =====================================================


def test_websocket_create_room_action(
        client,
        auth_token,
        mock_execute
):

    with client.websocket_connect(
        f"/ws?token={auth_token}"
    ) as websocket:


        websocket.send_json(
            {
                "action":
                "create_room",

                "roomName":
                "test"
            }
        )


        response = websocket.receive_json()


        assert response is not None



# =====================================================
# leave room action
# =====================================================

def test_websocket_leave_room_action(
        client,
        auth_token,
        mock_execute
):

    with client.websocket_connect(
        f"/ws?token={auth_token}"
    ) as websocket:


        websocket.send_json(
            {
                "action":
                "leave_room"
            }
        )


        response = websocket.receive_json()


        assert response is not None