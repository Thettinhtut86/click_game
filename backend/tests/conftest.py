import pytest
import json
import pathlib
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timedelta
from jose import jwt
from fastapi.testclient import TestClient
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from backend import server

FIXTURE_PATH = pathlib.Path(
    __file__
).parent / "fixtures"

@pytest.fixture
def users_fixture():

    with open(
        FIXTURE_PATH / "users.json"
    ) as f:

        return json.load(f)



@pytest.fixture
def rooms_fixture():

    with open(
        FIXTURE_PATH / "rooms.json"
    ) as f:

        return json.load(f)



@pytest.fixture
def game_fixture():

    with open(
        FIXTURE_PATH / "game_data.json"
    ) as f:

        return json.load(f)


@pytest.fixture
def mock_payload():
    return {
        "user_id": "1001",
        "userName": "player1",
        "color": "red"
    }


@pytest.fixture
def valid_token(mock_payload):
    from backend import server

    return server.create_access_token(mock_payload)


@pytest.fixture
def expired_token(mock_payload):
    from backend import server

    expire = timedelta(seconds=-1)

    return server.create_access_token(
        mock_payload,
        expires_delta=expire
    )


@pytest.fixture
def auth_header(valid_token):
    return {
        "Authorization": f"Bearer {valid_token}"
    }


@pytest.fixture
def mock_db():
    db = MagicMock()
    cursor = MagicMock()

    db.cursor.return_value = cursor
    db.commit = MagicMock()
    db.close = MagicMock()

    return db


@pytest.fixture
def async_socket():

    socket = AsyncMock()

    socket.send_json = AsyncMock()
    socket.receive_json = AsyncMock()
    socket.close = AsyncMock()

    return socket

@pytest.fixture
def client():

    return TestClient(
        server.app
    )


@pytest.fixture
async def async_client():

    transport = ASGITransport(
        app=server.app
    )

    async with AsyncClient(
        transport=transport,
        base_url="http://test"
    ) as client:

        yield client


@pytest.fixture
def auth_token():

    payload = {
        "user_id": "1",
        "userName": "testuser",
        "color": "red"
    }

    return server.create_access_token(
        payload
    )


@pytest.fixture
def auth_headers(auth_token):

    return {
        "Authorization":
        f"Bearer {auth_token}"
    }

@pytest.fixture
def websocket():
    return AsyncMock()

@pytest.fixture
def game_room():

    return {
        "r1":{
            "host":"1",

            "players":[
                {
                    "id":"1",
                    "name":"player1",
                    "color":"red"
                },
                {
                    "id":"2",
                    "name":"player2",
                    "color":"blue"
                }
            ],

            "option":"asc",

            "game_started":False
        }
    }

