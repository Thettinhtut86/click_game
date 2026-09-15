import pytest
import uuid

from backend import server


# =====================================================
# norm_id()
# =====================================================


def test_norm_id_number():

    assert server.norm_id(123) == "123"


def test_norm_id_string():

    assert server.norm_id("abc") == "abc"



def test_norm_id_none():

    result = server.norm_id(
        None
    )

    assert result is None



def test_norm_id_uuid():

    uid = uuid.uuid4()

    result = server.norm_id(
        uid
    )

    assert result == str(uid)



# =====================================================
# serialize_player()
# =====================================================


def test_serialize_player_complete():

    player = {
        "id":1,
        "name":"player1",
        "color":"red"
    }


    result = server.serialize_player(
        player
    )


    assert result["name"] == "player1"
    assert result["color"] == "red"



def test_serialize_player_missing_color():

    player = {
        "id":1,
        "name":"player1"
    }


    result = server.serialize_player(
        player
    )


    assert "color" in result



def test_serialize_player_missing_name():

    player = {
        "id":1,
        "color":"blue"
    }


    result = server.serialize_player(
        player
    )


    assert "name" in result



# =====================================================
# ensure_room()
# =====================================================


def test_ensure_room_empty():

    room = {}

    result = server.ensure_room(
        room
    )

    assert result



def test_ensure_room_existing():

    room = {
        "players":[]
    }


    result = server.ensure_room(
        room
    )


    assert result["players"] == []



def test_ensure_room_missing_host():

    room = {}

    result = server.ensure_room(
        room
    )


    assert "host" in result



def test_ensure_room_missing_option():

    room = {}

    result = server.ensure_room(
        room
    )


    assert "option" in result



def test_ensure_room_missing_bubbles():

    room = {}

    result = server.ensure_room(
        room
    )


    assert "bubbles" in result



def test_ensure_room_missing_players():

    room = {}

    result = server.ensure_room(
        room
    )


    assert "players" in result



def test_ensure_room_host_assigned():

    room = {
        "players":[
            {
                "id":123,
                "name":"Alice",
                "color":"red"
            }
        ]
    }

    result = server.ensure_room(room)


    assert result["host"] == "123"

def test_ensure_room_default_values():

    result = server.ensure_room({})

    assert result["players"] == []
    assert result["watchers"] == []
    assert result["game_started"] is False
    assert result["option"] == "asc"


def test_ensure_room_existing_host_kept():

    result = server.ensure_room({
        "host":"99",
        "players":[
            {
                "id":1,
                "name":"Alice"
            }
        ]
    })

    assert result["host"] == "99"



def test_ensure_room_player_id_normalized():

    result = server.ensure_room({
        "players":[
            {
                "id":123,
                "name":"Alice",
                "color":"red"
            }
        ]
    })

    assert result["players"][0]["id"] == "123"


# =====================================================
# generate_bubble_order()
# =====================================================


def test_generate_bubble_order_count():

    result = server.generate_bubble_order()


    assert len(result) == 100



def test_generate_bubble_order_unique():

    result = server.generate_bubble_order()


    assert len(
        set(result)
    ) == 100



def test_generate_bubble_order_range():

    result = server.generate_bubble_order()


    assert min(result) >= 1
    assert max(result) <= 100



def test_generate_bubble_order_random():

    first = server.generate_bubble_order()
    second = server.generate_bubble_order()


    assert first != second



# =====================================================
# get_minutes_until_midnight()
# =====================================================


def test_minutes_until_midnight_positive():

    result = server.get_minutes_until_midnight()


    assert result >= 0



def test_minutes_before_midnight():

    result = server.get_minutes_until_midnight()


    assert result <= 1440



def test_minutes_midnight():

    result = server.get_minutes_until_midnight()

    assert isinstance(
        result,
        int
    )