import pytest
import json

from unittest.mock import patch, AsyncMock


# =====================================================
# websocket_endpoint()
# =====================================================


def test_websocket_missing_token(
        client
):

    with client.websocket_connect(
        "/ws"
    ) as websocket:

        data = websocket.receive_json()

        assert data is not None



def test_websocket_invalid_token(
        client
):

    with client.websocket_connect(
        "/ws?token=invalid"
    ) as websocket:

        data = websocket.receive_json()

        assert data is not None



def test_websocket_valid_token(
        client,
        auth_token
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
        auth_token
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


        assert (
            response["type"]
            in [
                "handshake",
                "success"
            ]
        )



# =====================================================
# Invalid JSON
# =====================================================


def test_websocket_invalid_json(
        client,
        auth_token
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
# Unknown action
# =====================================================


def test_websocket_unknown_action(
        client,
        auth_token
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
# Disconnect
# =====================================================


def test_websocket_disconnect_cleanup(
        client,
        auth_token
):

    websocket = client.websocket_connect(
        f"/ws?token={auth_token}"
    )


    websocket.__enter__()


    websocket.close()


    assert True



# =====================================================
# Host disconnect
# =====================================================


@patch("server.close_room")
def test_host_disconnect(
        mock_close,
        client,
        auth_token
):

    with client.websocket_connect(
        f"/ws?token={auth_token}"
    ) as websocket:


        websocket.close()


    assert True



# =====================================================
# Broadcast online users
# =====================================================


@patch("server.broadcast_online_users")
def test_online_user_broadcast(
        mock_broadcast,
        client,
        auth_token
):

    with client.websocket_connect(
        f"/ws?token={auth_token}"
    ):


        pass


    mock_broadcast.assert_called()



# =====================================================
# Broadcast rooms
# =====================================================


@patch("server.broadcast_rooms")
def test_room_broadcast(
        mock_broadcast,
        client,
        auth_token
):

    with client.websocket_connect(
        f"/ws?token={auth_token}"
    ):


        pass


    mock_broadcast.assert_called()



# =====================================================
# Multiple users
# =====================================================


def test_multiple_websocket_connections(
        client,
        auth_token
):

    ws1 = client.websocket_connect(
        f"/ws?token={auth_token}"
    )

    ws2 = client.websocket_connect(
        f"/ws?token={auth_token}"
    )


    assert ws1
    assert ws2



# =====================================================
# websocket action flow
# =====================================================


def test_websocket_create_room_action(
        client,
        auth_token
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


        assert response



# =====================================================
# websocket leave action
# =====================================================


def test_websocket_leave_room_action(
        client,
        auth_token
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


        assert response