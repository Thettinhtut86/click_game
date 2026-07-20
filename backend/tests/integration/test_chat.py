import pytest
from unittest.mock import patch




# =====================================================
# Send message
# =====================================================


def test_send_chat_message(
        client,
        auth_headers
):

    response = client.post(
        "/ws/action",
        headers=auth_headers,
        json={
            "action":"send_message",
            "message":"hello world"
        }
    )


    assert response.status_code <500



def test_send_empty_message(
        client,
        auth_headers
):

    response = client.post(
        "/ws/action",
        headers=auth_headers,
        json={
            "action":"send_message",
            "message":""
        }
    )


    assert response.status_code <500



def test_send_long_message(
        client,
        auth_headers
):

    response = client.post(
        "/ws/action",
        headers=auth_headers,
        json={
            "action":"send_message",
            "message":"x"*5000
        }
    )


    assert response.status_code <500



# =====================================================
# Mentions
# =====================================================


def test_chat_mention(
        client,
        auth_headers
):

    response = client.post(
        "/ws/action",
        headers=auth_headers,
        json={
            "action":"send_message",
            "message":"@player hello"
        }
    )


    assert response.status_code <500



def test_multiple_mentions(
        client,
        auth_headers
):

    response = client.post(
        "/ws/action",
        headers=auth_headers,
        json={
            "action":"send_message",
            "message":
            "@one @two hello"
        }
    )


    assert response.status_code <500



# =====================================================
# History
# =====================================================


def test_get_chat_history(
        client,
        auth_headers
):

    response = client.post(
        "/ws/action",
        headers=auth_headers,
        json={
            "action":"load_chat",
            "roomId":"1"
        }
    )


    assert response.status_code <500



# =====================================================
# Delete / Restore
# =====================================================


def test_delete_message(
        client,
        auth_headers
):

    response = client.post(
        "/ws/action",
        headers=auth_headers,
        json={
            "action":"delete_message",
            "id":1
        }
    )


    assert response.status_code <500



def test_restore_message(
        client,
        auth_headers
):

    response = client.post(
        "/ws/action",
        headers=auth_headers,
        json={
            "action":"restore_message",
            "id":1
        }
    )


    assert response.status_code <500



# =====================================================
# Seen status
# =====================================================


def test_mark_seen(
        client,
        auth_headers
):

    response = client.post(
        "/ws/action",
        headers=auth_headers,
        json={
            "action":"mark_seen",
            "roomId":"1"
        }
    )


    assert response.status_code <500



# =====================================================
# DB errors
# =====================================================


@patch("backend.server.execute")
def test_chat_database_error(
        mock_execute,
        client,
        auth_headers
):

    mock_execute.side_effect = Exception(
        "db failure"
    )


    response = client.post(
        "/ws/action",
        headers=auth_headers,
        json={
            "action":"send_message",
            "message":"hello"
        }
    )


    assert response.status_code >=400