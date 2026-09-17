from datetime import timedelta

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from click_game.api.dependencies import authenticate_token
from click_game.core.security import create_access_token, verify_token


def test_AUTH001_create_token_valid_payload(mock_payload):
    token = create_access_token(mock_payload)
    assert isinstance(token, str)
    assert token


def test_AUTH002_create_token_custom_expiration(mock_payload):
    token = create_access_token(mock_payload, expires_delta=timedelta(minutes=60))
    decoded = verify_token(token)
    assert decoded is not None
    assert "exp" in decoded


def test_AUTH003_create_token_default_expiration(mock_payload):
    token = create_access_token(mock_payload)
    decoded = verify_token(token)
    assert decoded is not None
    assert "exp" in decoded


def test_AUTH004_payload_preserved(mock_payload):
    decoded = verify_token(create_access_token(mock_payload))
    assert decoded["user_id"] == "1001"
    assert decoded["userName"] == "player1"
    assert decoded["color"] == "red"


def test_AUTH005_verify_valid_token(valid_token):
    assert verify_token(valid_token) is not None


def test_AUTH006_invalid_signature(mock_payload):
    token = create_access_token(mock_payload)
    broken = token[:-5] + "xxxxx"
    assert verify_token(broken) is None


def test_AUTH007_expired_token(expired_token):
    assert verify_token(expired_token) is None


def test_AUTH008_empty_token():
    assert verify_token("") is None


def test_AUTH009_random_string():
    assert verify_token("abcdef123456") is None


def test_AUTH010_authenticate_token_valid(valid_token):
    payload = authenticate_token(valid_token)
    assert payload["user_id"] == "1001"


def test_AUTH011_authenticate_token_invalid():
    with pytest.raises(HTTPException) as exc:
        authenticate_token("invalid.token")
    assert exc.value.status_code == 401


def test_AUTH012_bearer_credentials_are_supported():
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="abc",
    )
    assert credentials.scheme == "Bearer"
    assert credentials.credentials == "abc"
