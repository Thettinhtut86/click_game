import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from datetime import timedelta


from backend import server


# =====================================================
# create_access_token()
# =====================================================


def test_AUTH001_create_token_valid_payload(mock_payload):

    token = server.create_access_token(
        mock_payload
    )

    assert token is not None
    assert isinstance(token, str)



def test_AUTH002_create_token_custom_expiration(mock_payload):

    token = server.create_access_token(
        mock_payload,
        expires_delta=timedelta(minutes=60)
    )

    decoded = server.verify_token(token)

    assert decoded is not None
    assert "exp" in decoded



def test_AUTH003_create_token_default_expiration(mock_payload):

    token = server.create_access_token(
        mock_payload
    )

    decoded = server.verify_token(token)

    assert "exp" in decoded



def test_AUTH004_payload_preserved(mock_payload):

    token = server.create_access_token(
        mock_payload
    )

    decoded = server.verify_token(token)

    assert decoded["user_id"] == "1001"
    assert decoded["userName"] == "player1"
    assert decoded["color"] == "red"



# =====================================================
# verify_token()
# =====================================================


def test_AUTH005_verify_valid_token(valid_token):

    result = server.verify_token(
        valid_token
    )

    assert result is not None



def test_AUTH006_invalid_signature(mock_payload):

    token = server.create_access_token(
        mock_payload
    )

    broken = token[:-5] + "xxxxx"

    result = server.verify_token(
        broken
    )

    assert result is None



def test_AUTH007_expired_token(expired_token):

    result = server.verify_token(
        expired_token
    )

    assert result is None



def test_AUTH008_empty_token():

    result = server.verify_token(
        ""
    )

    assert result is None



def test_AUTH009_random_string():

    result = server.verify_token(
        "abcdef123456"
    )

    assert result is None



# =====================================================
# get_current_user()
# =====================================================


def test_AUTH010_get_current_user_valid(valid_token):

    result = server.get_current_user(
        valid_token
    )

    assert result is not None



def test_AUTH011_get_current_user_invalid():

    with pytest.raises(Exception):

        server.get_current_user(
            "invalid.token"
        )



# =====================================================
# get_token_from_header()
# =====================================================


def test_AUTH012_valid_authorization_header(
        auth_header
):

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=
        auth_header["Authorization"].split()[1]
    )

    result = server.get_token_from_header(
        credentials
    )

    assert result is not None



def test_AUTH013_missing_header():

    with pytest.raises(HTTPException) as exc:

        server.get_token_from_header(
            None
        )

    assert exc.value.status_code == 401



def test_AUTH014_wrong_bearer_prefix():

    credentials = HTTPAuthorizationCredentials(
        scheme="Basic",
        credentials="abc"
    )

    with pytest.raises(HTTPException):
        server.get_token_from_header(credentials)



def test_AUTH015_invalid_jwt():

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="abc"
    )

    assert server.get_token_from_header(credentials) == "abc"