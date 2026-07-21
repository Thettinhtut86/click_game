from unittest.mock import patch


def test_rooms_empty(
        client,
        mock_execute
):

    response = client.get(
        "/rooms"
    )

    assert response.status_code == 200

    assert response.json() == []


def test_rooms_one_room(
        client,
        monkeypatch
):

    def fake_execute(
            query,
            params=None,
            fetch=False,
            dictionary=False
    ):

        return [
            {
                "id": "room1",
                "host_id": "1",
                "player_count": 2
            }
        ]


    monkeypatch.setattr(
        "backend.server.execute",
        fake_execute
    )


    response = client.get(
        "/rooms"
    )


    assert response.status_code == 200

    rooms = response.json()

    assert len(rooms) == 1

    assert rooms[0]["id"] == "room1"



def test_rooms_multiple_rooms(
        client,
        monkeypatch
):

    def fake_execute(
            query,
            params=None,
            fetch=False,
            dictionary=False
    ):

        return [
            {
                "id":"room1",
                "host_id":"1",
                "player_count":2
            },
            {
                "id":"room2",
                "host_id":"2",
                "player_count":4
            }
        ]


    monkeypatch.setattr(
        "backend.server.execute",
        fake_execute
    )


    response = client.get(
        "/rooms"
    )


    assert response.status_code == 200


    rooms = response.json()


    assert len(rooms) == 2



@patch("backend.server.execute")
def test_rooms_database_exception(
        mock_execute,
        client
):

    mock_execute.side_effect = Exception(
        "DB"
    )


    response = client.get(
        "/rooms"
    )


    assert response.status_code == 500

    assert response.json()["detail"] == "db error"