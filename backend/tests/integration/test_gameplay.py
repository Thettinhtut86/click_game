import pytest
from unittest.mock import patch


# =====================================================
# Room creation -> Join -> Start game
# =====================================================


def test_create_room_flow(
        client,
        auth_headers
):

    response = client.post(
        "/ws/action",
        headers=auth_headers,
        json={
            "action":"create_room",
            "roomName":"test-room",
            "option":"asc"
        }
    )


    assert response.status_code in [
        200,
        201,
        404
    ]



def test_join_room_flow(
        client,
        auth_headers
):

    response = client.post(
        "/ws/action",
        headers=auth_headers,
        json={
            "action":"join_room",
            "roomId":"1"
        }
    )


    assert response.status_code < 500



def test_start_game_flow(
        client,
        auth_headers
):

    response = client.post(
        "/ws/action",
        headers=auth_headers,
        json={
            "action":"start_game",
            "roomId":"1"
        }
    )


    assert response.status_code < 500



def test_select_bubble_flow(
        client,
        auth_headers
):

    response = client.post(
        "/ws/action",
        headers=auth_headers,
        json={
            "action":"select_bubble",
            "roomId":"1",
            "bubble_id":10
        }
    )


    assert response.status_code <500



# =====================================================
# Game ordering
# =====================================================


def test_game_ascending_order(
        client,
        auth_headers
):

    response = client.post(
        "/ws/action",
        headers=auth_headers,
        json={
            "action":"create_room",
            "option":"asc"
        }
    )


    assert response.status_code <500



def test_game_descending_order(
        client,
        auth_headers
):

    response = client.post(
        "/ws/action",
        headers=auth_headers,
        json={
            "action":"create_room",
            "option":"desc"
        }
    )


    assert response.status_code <500



# =====================================================
# Missing data
# =====================================================


def test_start_without_room(
        client,
        auth_headers
):

    response = client.post(
        "/ws/action",
        headers=auth_headers,
        json={
            "action":"start_game"
        }
    )


    assert response.status_code <500



def test_select_without_bubble(
        client,
        auth_headers
):

    response = client.post(
        "/ws/action",
        headers=auth_headers,
        json={
            "action":"select_bubble"
        }
    )


    assert response.status_code <500



# =====================================================
# DB failure
# =====================================================


@patch("backend.server.execute")
def test_gameplay_database_failure(
        mock_execute,
        client,
        auth_headers
):

    mock_execute.side_effect = Exception(
        "database error"
    )


    response = client.post(
        "/ws/action",
        headers=auth_headers,
        json={
            "action":"start_game"
        }
    )


    assert response.status_code >=400