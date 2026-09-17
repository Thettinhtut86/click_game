from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from click_game.core.security import create_access_token
from click_game.main import app
from click_game.state.connections import connection_store
from click_game.state.rooms import room_store


@pytest.fixture(autouse=True)
def clean_runtime_state():
    connection_store.connections.clear()
    room_store.clear()
    yield
    connection_store.connections.clear()
    room_store.clear()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_ws():
    websocket = AsyncMock()
    return websocket


@pytest.fixture
def mock_payload():
    return {
        "user_id": "1001",
        "userName": "player1",
        "color": "red",
    }


@pytest.fixture
def valid_token(mock_payload):
    return create_access_token(mock_payload)


@pytest.fixture
def expired_token(mock_payload):
    return create_access_token(
        mock_payload,
        expires_delta=timedelta(seconds=-1),
    )


@pytest.fixture
def auth_headers(valid_token):
    return {"Authorization": f"Bearer {valid_token}"}


@pytest.fixture
def fixture_path():
    return Path(__file__).parent / "fixtures"
