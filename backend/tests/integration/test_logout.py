from unittest.mock import patch
from backend import server

def test_logout_success(client):
    with patch("backend.server.execute") as mock_execute:
        mock_execute.return_value = 1
        mock_execute.side_effect = [
            1,      
            []      
        ]

        response = client.post(
            "/logout",
            json={
                "user_id": "1"
            }
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "logged_out"
        assert body["userId"] == "1"



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
    with patch("backend.server.execute") as mock_execute:
        mock_execute.side_effect = [1, []]

        response = client.post("/logout", json={"user_id": "1"})
        assert response.status_code == 200



def test_logout_remove_player(client):
    server.rooms_state = {
        "r1": {
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
            "watchers": []
        }
    }


    with patch("backend.server.execute") as mock_execute:
        mock_execute.side_effect  = [1, []]
        response = client.post(
            "/logout",
            json={
                "user_id": "1"
            }
        )

        assert response.status_code == 200
        assert len(
            server.rooms_state["r1"]["players"]
        ) == 1

        assert (
            server.rooms_state["r1"]["players"][0]["id"]
            == "2"
        )
