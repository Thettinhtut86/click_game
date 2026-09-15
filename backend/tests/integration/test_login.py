import pytest
from unittest.mock import patch


# =====================================================
# POST /login
# =====================================================


def test_login_valid(client):

    with patch(
        "backend.server.execute"
    ) as mock_execute:

        mock_execute.side_effect = [
            [],   # SELECT existing players
            1     # INSERT player id
        ]

        response = client.post(
            "/login",
            json={
                "user_name": "player1"
            }
        )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["userName"] == "player1"
    assert "token" in body



def test_login_missing_username(client):

    response = client.post(
        "/login",
        json={}
    )

    assert response.status_code == 400



def test_login_max_players(client):

    with patch(
        "backend.server.execute"
    ) as mock_execute:

        mock_execute.return_value = [
            {"id": i, "name": f"user{i}", "color": "red"}
            for i in range(12)
        ]

        response = client.post(
            "/login",
            json={
                "user_name": "player2"
            }
        )

    assert response.status_code == 400



def test_login_no_colors(client):

    with patch(
        "backend.server.execute"
    ) as mock_execute:

        mock_execute.return_value = [
            {
                "id":1,
                "name":"player1",
                "color":"red"
            },
            {
                "id":2,
                "name":"player2",
                "color":"blue"
            }
        ]

        with patch(
            "backend.server.PLAYER_COLORS",
            []
        ):

            response = client.post(
                "/login",
                json={
                    "user_name":"player1"
                }
            )

    assert response.status_code == 400



def test_login_database_exception(client):

    with patch(
        "backend.server.execute"
    ) as mock_execute:

        mock_execute.side_effect = Exception(
            "DB Error"
        )

        response = client.post(
            "/login",
            json={
                "user_name":"player1"
            }
        )

    assert response.status_code == 500