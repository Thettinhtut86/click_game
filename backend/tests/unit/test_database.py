import pytest
from unittest.mock import MagicMock, patch

from backend import server


# =====================================================
# execute()
# =====================================================


@patch("backend.server.mysql.connector.connect")
def test_DB001_select_query(mock_connect):

    cursor = MagicMock()

    cursor.fetchall.return_value = [
        ("1", "player1")
    ]

    conn = MagicMock()
    conn.cursor.return_value = cursor

    mock_connect.return_value = conn


    result = server.execute(
        "SELECT * FROM players",
        fetch=True
    )


    assert result == [
        ("1", "player1")
    ]



@patch("backend.server.mysql.connector.connect")
def test_DB002_insert_commit(mock_connect):

    conn = MagicMock()
    mock_connect.return_value = conn

    server.execute(
        """
        INSERT INTO players(name)
        VALUES('test')
        """,
        commit=True
    )

    conn.commit.assert_called_once()



@patch("backend.server.mysql.connector.connect")
def test_DB003_update_commit(mock_connect):

    conn = MagicMock()
    mock_connect.return_value = conn

    server.execute(
        "UPDATE players SET name='x'",
        commit=True
    )

    conn.commit.assert_called_once()



@patch("backend.server.mysql.connector.connect")
def test_DB004_delete_commit(mock_connect):

    conn = MagicMock()
    mock_connect.return_value = conn

    server.execute(
        "DELETE FROM players WHERE id=1",
        commit=True
    )

    conn.commit.assert_called_once()



@patch("backend.server.mysql.connector.connect")
def test_DB005_fetch_true(mock_connect):

    cursor = MagicMock()

    cursor.fetchall.return_value = [
        {"id":1}
    ]

    conn = MagicMock()
    conn.cursor.return_value = cursor

    mock_connect.return_value = conn


    result = server.execute(
        "SELECT id FROM players",
        fetch=True
    )


    assert result



@patch("backend.server.mysql.connector.connect")
def test_DB006_dictionary_true(mock_connect):

    cursor = MagicMock()

    conn = MagicMock()

    conn.cursor.return_value = cursor

    mock_connect.return_value = conn


    server.execute(
        "SELECT * FROM players",
        dictionary=True
    )


    conn.cursor.assert_called()



@patch("backend.server.mysql.connector.connect")
def test_DB007_mysql_connection_failure(mock_connect):

    mock_connect.side_effect = Exception(
        "connection failed"
    )


    with pytest.raises(Exception):

        server.execute(
            "SELECT 1"
        )



@patch("backend.server.mysql.connector.connect")
def test_DB008_sql_syntax_error(mock_connect):

    cursor = MagicMock()

    cursor.execute.side_effect = Exception(
        "syntax error"
    )

    conn = MagicMock()

    conn.cursor.return_value = cursor

    mock_connect.return_value = conn


    with pytest.raises(Exception):

        server.execute(
            "BAD SQL"
        )



@patch("backend.server.mysql.connector.connect")
def test_DB009_cursor_closed(mock_connect):

    conn = MagicMock()

    cursor = MagicMock()

    conn.cursor.return_value = cursor

    mock_connect.return_value = conn


    server.execute(
        "SELECT 1"
    )


    cursor.close.assert_called()



@patch("backend.server.mysql.connector.connect")
def test_DB010_connection_closed(mock_connect):

    conn = MagicMock()

    mock_connect.return_value = conn


    server.execute(
        "SELECT 1"
    )


    conn.close.assert_called()