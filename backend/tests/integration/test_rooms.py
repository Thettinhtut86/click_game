from unittest.mock import patch



def test_rooms_empty(client):

    response = client.get(
        "/rooms"
    )


    assert response.status_code == 200



def test_rooms_one_room(client):

    response = client.get(
        "/rooms"
    )


    assert isinstance(
        response.json(),
        list
    )



def test_rooms_multiple_rooms(client):

    response = client.get(
        "/rooms"
    )


    assert response.status_code == 200



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


    assert response.status_code >=400