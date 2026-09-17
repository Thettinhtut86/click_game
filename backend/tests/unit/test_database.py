from unittest.mock import MagicMock, patch

import mysql.connector
import pytest

from click_game.db import database


@pytest.fixture(autouse=True)
def reset_pool():
    database.close_database()
    yield
    database.close_database()


@patch("click_game.db.database.mysql.connector.connect")
def test_DB001_select_query(mock_connect):
    cursor = MagicMock()
    cursor.fetchall.return_value = [("1", "player1")]
    conn = MagicMock()
    conn.cursor.return_value = cursor
    mock_connect.return_value = conn

    result = database.execute("SELECT * FROM players", fetch=True)

    assert result == [("1", "player1")]
    cursor.close.assert_called_once()
    conn.close.assert_called_once()


@patch("click_game.db.database.mysql.connector.connect")
def test_DB002_insert_commit(mock_connect):
    conn = MagicMock()
    conn.cursor.return_value = MagicMock(lastrowid=7)
    mock_connect.return_value = conn

    result = database.execute("INSERT INTO players(name) VALUES(%s)", ("test",), commit=True)

    assert result == conn.cursor.return_value.lastrowid
    conn.commit.assert_called_once()


@patch("click_game.db.database.mysql.connector.connect")
def test_DB003_update_commit(mock_connect):
    conn = MagicMock()
    conn.cursor.return_value = MagicMock(lastrowid=0)
    mock_connect.return_value = conn

    database.execute("UPDATE players SET name=%s", ("x",), commit=True)
    conn.commit.assert_called_once()


@patch("click_game.db.database.mysql.connector.connect")
def test_DB004_delete_commit(mock_connect):
    conn = MagicMock()
    conn.cursor.return_value = MagicMock(lastrowid=0)
    mock_connect.return_value = conn

    database.execute("DELETE FROM players WHERE id=1", commit=True)
    conn.commit.assert_called_once()


@patch("click_game.db.database.mysql.connector.connect")
def test_DB005_fetch_true_returns_empty_list_for_no_rows(mock_connect):
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    conn = MagicMock()
    conn.cursor.return_value = cursor
    mock_connect.return_value = conn

    assert database.execute("SELECT 1", fetch=True) == []


@patch("click_game.db.database.mysql.connector.connect")
def test_DB006_dictionary_true(mock_connect):
    conn = MagicMock()
    conn.cursor.return_value = MagicMock()
    mock_connect.return_value = conn

    database.execute("SELECT * FROM players", dictionary=True)

    conn.cursor.assert_called_once_with(dictionary=True)


@patch("click_game.db.database.mysql.connector.connect")
def test_DB007_mysql_connection_failure_is_tolerated(mock_connect):
    mock_connect.side_effect = mysql.connector.Error("connection failed")
    assert database.execute("SELECT 1") is None


@patch("click_game.db.database.mysql.connector.connect")
def test_DB008_sql_error_is_tolerated(mock_connect):
    cursor = MagicMock()
    cursor.execute.side_effect = mysql.connector.Error("syntax error")
    conn = MagicMock()
    conn.cursor.return_value = cursor
    mock_connect.return_value = conn

    assert database.execute("BAD SQL") is None


@patch("click_game.db.database.mysql.connector.connect")
def test_DB009_fetch_error_returns_empty_list(mock_connect):
    mock_connect.side_effect = mysql.connector.Error("failure")
    assert database.execute("SELECT 1", fetch=True) == []


@patch("click_game.db.database.mysql.connector.pooling.MySQLConnectionPool")
def test_initialize_database_creates_pool(mock_pool):
    database.initialize_database()
    mock_pool.assert_called_once()


@patch("click_game.db.database.mysql.connector.pooling.MySQLConnectionPool")
def test_initialize_database_error_is_tolerated(mock_pool):
    mock_pool.side_effect = mysql.connector.Error("pool failure")
    database.initialize_database()
    assert database._pool is None


@patch("click_game.db.database.execute")
def test_fetch_one_returns_first_row(mock_execute):
    mock_execute.return_value = [{"id": 1}, {"id": 2}]
    assert database.fetch_one("SELECT 1") == {"id": 1}


@patch("click_game.db.database.execute")
def test_fetch_one_returns_none_when_empty(mock_execute):
    mock_execute.return_value = []
    assert database.fetch_one("SELECT 1") is None


@patch("click_game.db.database.execute")
def test_fetch_all_returns_rows(mock_execute):
    mock_execute.return_value = [{"id": 1}]
    assert database.fetch_all("SELECT 1") == [{"id": 1}]


@patch("click_game.db.database.execute")
def test_fetch_all_returns_empty_when_none(mock_execute):
    mock_execute.return_value = None
    assert database.fetch_all("SELECT 1") == []
