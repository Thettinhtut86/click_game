from unittest.mock import patch


def test_logout_success(client):

    response = client.post(
        "/logout",
        json={
            "user_id": "1"
        }
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "logged_out"



def test_logout_missing_uid(client):

    response = client.post(
        "/logout",
        json={}
    )

    assert response.status_code == 400



def test_logout_invalid_uid(client):

    response = client.post(
        "/logout",
        json={
            "uid": "xxxx"
        }
    )

    assert response.status_code == 400



@patch("backend.server.execute")
def test_logout_db_failure(
        mock_execute,
        client
):

    mock_execute.side_effect = Exception(
        "DB error"
    )

    response = client.post(
        "/logout",
        json={
            "user_id": "1"
        }
    )

    assert response.status_code == 500



def test_logout_connected_websocket(client):

    response = client.post(
        "/logout",
        json={
            "user_id": "1"
        }
    )

    assert response.status_code == 200



def test_logout_remove_player(client):

    response = client.post(
        "/logout",
        json={
            "user_id": "1"
        }
    )

    assert response.status_code < 500