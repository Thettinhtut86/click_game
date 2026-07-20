# server.py
import re
import json
import logging
import asyncio
import random
import mysql.connector
from mysql.connector import Error
from fastapi import BackgroundTasks, FastAPI, WebSocket, WebSocketDisconnect, Body, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials
from datetime import datetime, timedelta, time, timezone
from typing import Dict, Optional
from jose import JWTError, jwt
from urllib.parse import parse_qs

# ---------- Configuration ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("bubble-game")

DB_CONFIG = {
    "host": "192.168.250.3",
    "user": "root",
    "password": "root",
    "database": "live_game"
}

PLAYER_COLORS = [
    "#e6194b", "#3cb44b", "#ffe119", "#437fd8",
    "#f58231", "#440568", "#46f0f0", "#f032e6",
    "#1d0a0a", "#fabebe", "#008080", "#2600ff"
]

ACTION_HANDLERS = {
    "handshake": lambda ws, uid, name, data: handle_handshake(ws, uid, name),
    "create_room": lambda ws, uid, name, data: handle_create_room(ws, uid, name, data),
    "join_room": lambda ws, uid, name, data: handle_join_room(ws, uid, name, data),
    "leave_room": lambda ws, uid, name, data: handle_leave_room(ws, uid, data),
    "start_game": lambda ws, uid, name, data: handle_start_game(ws, uid, data),
    "quit_room": lambda ws, uid, name, data: handle_quit_room(ws, uid, data),
    "select_bubble": lambda ws, uid, name, data: handle_select_bubble(ws, uid, data),
    "send_message": lambda ws, uid, name, data: handle_send_message(ws, uid, name, data),
    "load_chat": lambda ws, uid, name, data: send_chat_history(ws),
    "typing_start": lambda ws, uid, name, data: handle_typing_start(uid, name),
    "typing_stop": lambda ws, uid, name, data: handle_typing_stop(uid, name),
    "delete_message": lambda ws, uid, name, data: handle_delete_message(uid, data),
    "restore_message": lambda ws, uid, name, data: handle_restore_message(uid, data),
    "get_rooms": lambda ws, uid, name, data: handle_get_rooms(ws, uid, name, data),
}

# ---------- FastAPI Setup ----------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- In-Memory State ----------
rooms_state: Dict[str, dict] = {}
connected_clients: Dict[str, WebSocket] = {}
chat_messages = []
typing_users = {}
MAX_CHAT_MESSAGES = 1000
MENTION_REGEX = r"@([a-zA-Z0-9_]+)"
SECRET_KEY = "y9UCH4fYAqOqIIz3YmqZGo5zAc4wF3MT1WBFGqANbw0"
ALGORITHM = "HS256"


# ---------- Database Helper ----------
def execute(
    query: str,
    params: tuple = None,
    fetch: bool = False,
    dictionary: bool = False,
    commit: bool = False
):
    conn = None
    cursor = None

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=dictionary)

        cursor.execute(query, params or ())

        if commit:
            conn.commit()
            return cursor.lastrowid

        if fetch:
            return cursor.fetchall() or []

        return None

    except Error as e:
        logger.error("DB Error: %s", e)

        # CI/CD should not crash because DB is unavailable
        if fetch:
            return []

        return None

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ---------- Safe Query Helpers ----------
def fetch_one(query, params=None):

    rows = execute(
        query,
        params=params,
        fetch=True,
        dictionary=True
    )

    if not rows:
        return None

    return rows[0]


def fetch_all(query: str, params: tuple = None):
    rows = execute(
        query=query,
        params=params,
        fetch=True,
        dictionary=True
    )

    return rows if rows else []

def get_rooms_data():
    rooms = execute(
        """
        SELECT r.id,
               r.host_id,
               h.name AS host_name,
               r.created_at,
               COUNT(p.id) AS player_count
        FROM rooms r
        LEFT JOIN players p ON p.room_id = r.id
        LEFT JOIN players h ON h.id = r.host_id
        GROUP BY r.id, r.host_id, h.name, r.created_at
        ORDER BY r.id DESC
        """,
        fetch=True,
        dictionary=True
    ) or []

    for room in rooms:
        if room.get("created_at"):
            room["created_at"] = room["created_at"].strftime("%Y-%m-%d %H:%M:%S")

    return rooms

def serialize_player(p: dict) -> dict:
    return {
        "id": str(p["id"]),
        "name": p.get("name"),
        "color": p.get("color")
    }            

# ---------- Utility Functions ----------
def norm_id(x) -> str | None:
    if x is None:
        return None

    return str(x)

def ensure_room(room: dict) -> dict:
    room.setdefault("players", [])
    room.setdefault("watchers", [])
    room.setdefault("bubbles", {})
    room.setdefault("game_started", False)
    room.setdefault("option", "asc")
    room.setdefault("host", None)
    room.setdefault("index", 0)
    room.setdefault("play_order", [])
    room.setdefault("display_order", [])
    room["players"] = [
        {
            "id": str(p.get("id")),
            "name": p.get("name"),
            "color": p.get("color")
        }
        for p in room["players"]
    ]
    if not room["host"] and room["players"]:
        room["host"] = room["players"][0]["id"]
    return room

def get_player_color(player: dict, room: dict, uid: str) -> str:
    """Assign or retrieve player color."""
    if player.get("color"):
        return player["color"]
    
    try:
        row = execute("SELECT color FROM players WHERE id=%s", (uid,), fetch=True, dictionary=True)
        if row and row[0].get("color"):
            player["color"] = row[0]["color"]
            return player["color"]
    except Exception:
        logger.exception("Failed to fetch player color")
    
    used_colors = {p["color"] for p in room["players"] if p.get("color")}
    available_colors = [c for c in PLAYER_COLORS if c not in used_colors]
    color = available_colors[0] if available_colors else "#000000"
    player["color"] = color
    
    try:
        execute("UPDATE players SET color=%s WHERE id=%s", (color, uid), commit=True)
    except Exception:
        logger.exception("Failed to save player color")
    
    return color

def get_minutes_until_midnight() -> int:
    now = datetime.now()

    tomorrow = now + timedelta(days=1)
    midnight = datetime.combine(tomorrow.date(), time.min)
    
    minutes_remaining = int((midnight - now).total_seconds() / 60)
    
    return max(1, minutes_remaining)
ACCESS_TOKEN_EXPIRE_MINUTES = get_minutes_until_midnight() 

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload  
    except JWTError:
        return None

def get_current_user(token: str):    
    payload = verify_token(token)
    if not payload:
        raise Exception("Invalid token")
    return payload

def get_token_from_header(
    credentials: HTTPAuthorizationCredentials
):
    
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing"
        )
    
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication scheme"
        )

    return credentials.credentials

# ---------- Broadcast Functions ----------
async def broadcast_to_all(message: dict):
    """Send message to all connected clients."""
    for ws in connected_clients.values():
        try:
            await ws.send_text(json.dumps(message))
        except Exception:
            pass

async def broadcast_to_room(room_id: str, message: dict):
    """Send message to all players in a specific room."""
    room = rooms_state.get(str(room_id))
    if not room:
        return
    
    targets = set()
    for p in room["players"]:
        targets.add(str(p["id"]))

    for w in room.get("watchers", []):
        targets.add(str(w["id"]))

    for uid in targets:
        ws = connected_clients.get(uid)
        if ws:
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                pass

async def broadcast_rooms():
    await broadcast_to_all({"action": "rooms_update", "rooms": get_rooms_data()})

async def broadcast_room_update(room_id: str):
    """Broadcast updated room state to all connected clients."""
    state = rooms_state.get(str(room_id))
    if not state:
        return
    
    message = {
        "action": "room_update",
        "roomId": str(room_id),
        "players": [serialize_player(p) for p in state.get("players", [])],
        "watchers": state.get("watchers", []),
        "hostId": str(state.get("host")) if state.get("host") else None
    }
    await broadcast_to_all(message)

async def broadcast_chat_message(message: dict):
    await broadcast_to_all({
        "action": "new_message",
        "message": message
    })

async def broadcast_typing(action: str, uid: str, name: str):

    await broadcast_to_all({
        "action": action,
        "uid": uid,
        "name": name
    })

async def broadcast_online_users():
    users = []
    for uid in connected_clients.keys():
        row = execute("""
            SELECT id,name,color FROM players WHERE id=%s
        """, (uid,), fetch=True, dictionary=True)

        if row:
            users.append(row[0])

    await broadcast_to_all({
        "action": "online_users",
        "users": users
    })

# ---------- Room Management ----------
async def remove_player_from_room(player_id: str, room_id: str = None):
    """Remove player from room(s) and update database."""
    target_rooms = [str(room_id)] if room_id else list(rooms_state.keys())
    
    for rid in target_rooms:
        if rid in rooms_state:
            room = rooms_state[rid]
            room["players"] = [p for p in room["players"] if str(p["id"]) != str(player_id)]
            room["watchers"] = [w for w in room.get("watchers", []) if str(w["id"]) != str(player_id)]
            
            if not room["players"] and not room.get("watchers"):
                rooms_state.pop(rid, None)
                try:
                    execute("DELETE FROM rooms WHERE id=%s", (rid,), commit=True)
                    await broadcast_rooms()
                except Exception:
                    logger.exception("Failed to delete empty room")
            else:
                await broadcast_room_update(rid)
    
    try:
        execute("UPDATE players SET room_id=NULL WHERE id=%s", (player_id,), commit=True)
    except Exception:
        logger.exception("Failed to clear player's room assignment")

async def close_room(room_id: str, reason: str = "Host has quit. Room closed."):
    """Close a room and notify all players."""
    room = rooms_state.get(room_id)
    if not room:
        return
    
    message = {"action": "room_closed", "roomId": room_id, "message": reason}
    
    for player in room["players"]:
        ws = connected_clients.get(str(player["id"]))
        if ws:
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                pass
    
    for watcher in room.get("watchers", []):
        ws = connected_clients.get(str(watcher["id"]))
        if ws:
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                pass
    
    try:
        execute("DELETE FROM rooms WHERE id=%s", (room_id,), commit=True)
        execute("UPDATE players SET room_id=NULL WHERE room_id=%s", (room_id,), commit=True)
    except Exception:
        logger.exception("Failed to delete room from database")
    
    rooms_state.pop(room_id, None)
    await broadcast_rooms()


# ---------- Game Logic ----------
def generate_bubble_order(option: str = "asc") -> list:
    """Generate randomized bubble order for game."""
    numbers = list(range(1, 101))
    random.shuffle(numbers)
    return numbers

async def handle_game_end(room_id: str):
    """Handle end of game scoring and winner determination."""
    room = rooms_state.get(room_id)
    if not room:
        return
    
    scores = {}
    for bubble_owner in room["bubbles"].values():
        if bubble_owner:
            pid = bubble_owner["uid"]
            scores[pid] = scores.get(pid, 0) + 1
    
    max_score = max(scores.values()) if scores else 0
    winners = [pid for pid, score in scores.items() if score == max_score]
    
    winner_players = [
        p for p in room["players"] 
        if str(p["id"]) in winners
    ]
    
    await broadcast_to_room(room_id, {
        "action": "end_game",
        "roomId": room_id,
        "winners": winner_players,
        "is_tie": len(winners) > 1,
        "scores": scores
    })
    
    winner_ids = ",".join(winners) if len(winners) > 1 else winners[0] if winners else None
    try:
        execute("UPDATE rooms SET winner_id=%s, started=0 WHERE id=%s", (winner_ids, room_id), commit=True)
    except Exception:
        logger.exception("Failed to update winner")
    
    rooms_state.pop(room_id, None)
    await broadcast_rooms()

# ---------- WebSocket Handlers ----------
async def handle_handshake(ws: WebSocket, uid: str, name: str):
    """Handle WebSocket handshake."""
    await ws.send_text(json.dumps({
        "action": "handshake_ack",
        "status": "connected",
        "userId": uid,
        "userName": name
    }))

async def handle_create_room(ws: WebSocket, uid: str, name: str, data: dict):
    """Handle room creation via WebSocket."""
    try:
        option = data.get("option", "asc")
        room_id = str(execute(
            "INSERT INTO rooms (host_id, created_at) VALUES (%s, NOW())",
            (uid,), commit=True
        ))
        
        execute("UPDATE players SET room_id=%s WHERE id=%s", (room_id, uid), commit=True)
        
        # Get player info from database
        player_row = execute("SELECT name, color FROM players WHERE id=%s", (uid,), fetch=True, dictionary=True)
        player_info = {"id": uid, "name": name, "color": player_row[0]["color"] if player_row else None}
        
        rooms_state[room_id] = ensure_room({
            "host": uid,
            "option": option,
            "players": [player_info]
        })
        
        await ws.send_text(json.dumps({
            "action": "room_created",
            "roomId": room_id,
            "hostId": uid
        }))
        
        await broadcast_room_update(room_id)
        
    except Exception as e:
        logger.exception("Failed to create room: %s", e)
        await ws.send_text(json.dumps({"action": "error", "message": "Failed to create room"}))

async def handle_join_room(ws: WebSocket, uid: str, name: str, data: dict):
    """Handle player joining a room."""
    room_id = str(data.get("roomId"))
    
    if not room_id:
        await ws.send_text(json.dumps({"action": "error", "message": "roomId required"}))
        return
    
    # Load room from DB if not in memory
    if room_id not in rooms_state:
        row = execute("SELECT host_id FROM rooms WHERE id=%s", (room_id,), fetch=True, dictionary=True)
        if not row:
            await ws.send_text(json.dumps({"action": "error", "message": "Room not found"}))
            return
        
        players = execute(
            "SELECT id, name, color FROM players WHERE room_id=%s",
            (room_id,), fetch=True, dictionary=True
        ) or []
        
        rooms_state[room_id] = ensure_room({
            "host": str(row[0]["host_id"]),
            "players": players,
            "watchers": []
        })
    
    room = ensure_room(rooms_state[room_id])
    
    if room["game_started"]:
        await ws.send_text(json.dumps({"action": "error", "message": "Game already started"}))
        return
    
    # Check if player is already in room
    if any(str(p["id"]) == str(uid) for p in room["players"]):
        await ws.send_text(json.dumps({"action": "join_ack", "roomId": room_id}))
        await broadcast_room_update(room_id)
        return
    
    # Add as watcher if room is full (max 4 players)
    if len(room["players"]) >= 4:
        room["watchers"].append({"id": uid, "name": name})
        await ws.send_text(json.dumps({"action": "watcher_joined", "roomId": room_id}))
        await broadcast_room_update(room_id)
        return
    
    # Add player to room
    execute("UPDATE players SET room_id=%s WHERE id=%s", (room_id, uid), commit=True)
    
    # Get player color
    player_row = execute("SELECT color FROM players WHERE id=%s", (uid,), fetch=True, dictionary=True)
    player_info = {
        "id": uid, 
        "name": name, 
        "color": player_row[0]["color"] if player_row else None
    }
    room["players"].append(serialize_player(player_info))
    
    await ws.send_text(json.dumps({"action": "join_ack", "roomId": room_id}))
    await broadcast_room_update(room_id)
    await broadcast_rooms()

async def handle_leave_room(ws: WebSocket, uid: str, data: dict):
    """Handle player leaving a room."""
    room_id = str(data.get("roomId"))
    
    if not room_id:
        await ws.send_text(json.dumps({"action": "error", "message": "roomId required"}))
        return
    
    room = rooms_state.get(room_id)
    
    if not room:
        return
    
    if room.get("game_started"):
        logger.info("Ignoring leave_room during active game")
        return
    
    await remove_player_from_room(uid, room_id)
    await ws.send_text(json.dumps({"action": "leave_ack", "roomId": room_id}))
    await broadcast_rooms()

async def handle_start_game(ws: WebSocket, uid: str, data: dict):

    room_id = str(data.get("roomId"))

    if not room_id:
        await ws.send_text(json.dumps({
            "action":"error",
            "message":"roomId required"
        }))
        return

    room = rooms_state.get(room_id)

    if not room:
        await ws.send_text(json.dumps({
            "action":"error",
            "message":"Room not found"
        }))
        return

    if str(uid) != str(room.get("host")):
        await ws.send_text(json.dumps({
            "action":"error",
            "message":"Only host can start the game"
        }))
        return

    displayOrder = generate_bubble_order()

    if room.get("option") == "desc":
        play_order = list(range(100,0,-1))
    else:
        play_order = list(range(1,101))

    room["play_order"] = play_order
    room["display_order"] = displayOrder
    room["index"] = 0
    room["game_started"] = True
    room["bubbles"] = {
        f"B{i}":None 
        for i in displayOrder
    }

    try:
        execute(
            "UPDATE rooms SET started=1 WHERE id=%s",
            (room_id,),
            commit=True
        )

    except Exception:
        logger.exception(
            "Failed to update room started status"
        )

    await broadcast_to_room(
        room_id,
        {
            "action":"game_started",
            "roomId":room_id,
            "bubbles":room["bubbles"],
            "players":room["players"],
            "play_order":room["play_order"],
            "display_order":room["display_order"],
            "option":room["option"]
        }
    )

async def handle_quit_room(ws: WebSocket, uid: str, data: dict):
    """Handle player quitting a room."""
    room_id = str(data.get("roomId") or data.get("room_id"))
    
    if not room_id:
        await ws.send_text(json.dumps({"action": "error", "message": "roomId required"}))
        return
    
    room = rooms_state.get(room_id)
    if not room:
        await ws.send_text(json.dumps({"action": "error", "message": "Room not found"}))
        return
    
    # If host quits, close entire room
    if str(uid) == str(room.get("host")):
        await close_room(room_id)
        return
    
    # Remove player from room
    await remove_player_from_room(uid, room_id)
    await broadcast_rooms()
    await ws.send_text(json.dumps({"action": "quit_ack", "roomId": room_id}))

async def handle_select_bubble(ws: WebSocket, uid: str, data: dict):
    """Handle bubble selection during gameplay."""
    room_id = str(data.get("roomId") or data.get("room_id"))
    bubble_id = data.get("bubble_id")
    
    if not room_id or not bubble_id:
        await ws.send_text(json.dumps({"action": "error", "message": "roomId and bubble_id required"}))
        return
    
    room = rooms_state.get(room_id)
    if not room or not room.get("game_started"):
        await ws.send_text(json.dumps({"action": "error", "message": "Game not started or room not found"}))
        return
    
    # Validate correct bubble selection
    if room["index"] >= len(room["play_order"]):
        await ws.send_text(json.dumps({"action": "error", "message": "Game is over"}))
        return
    
    expected_label = f"B{room['play_order'][room['index']]}"
    if bubble_id != expected_label:
        await ws.send_text(json.dumps({
            "action": "error",
            "message": f"You must click {expected_label} next!"
        }))
        return
    
    # Ensure player exists in room
    player = next((p for p in room["players"] if str(p["id"]) == str(uid)), None)
    if not player:
        player = {"id": uid, "name": data.get("name", "Unknown"), "color": None}
        room["players"].append(player)
    
    # Assign player color
    player["color"] = get_player_color(player, room, uid)
    
    # Claim bubble
    room["bubbles"][bubble_id] = {"uid": uid, "color": player["color"]}
    room["index"] += 1
    
    # Broadcast bubble update
    await broadcast_to_room(room_id, {
        "action": "update_bubbles",
        "roomId": room_id,
        "bubbles": room["bubbles"],
        "currentIndex": room["index"]
    })
    
    # Check if game is complete
    if room["index"] >= len(room["play_order"]):
        await handle_game_end(room_id)

async def handle_typing_stop(uid: str, name: str):

    typing_users.pop(uid, None)

    await broadcast_typing(
        "typing_stop",
        uid,
        name
    )

async def handle_typing_start(uid: str, name: str):

    typing_users[uid] = datetime.now()

    await broadcast_typing(
        "typing_start",
        uid,
        name
    )

async def handle_send_message(ws, uid, name, data):
    text = data.get("text", "").strip()
    if not text or len(text) > 300:
        return

    player = execute(
        "SELECT color FROM players WHERE id=%s",
        (uid,),
        fetch=True,
        dictionary=True
    )
    color = player[0]["color"] if player else "#ffffff"

    # INSERT MESSAGE
    msg_id = execute("""
        INSERT INTO daily_chat
        (player_id, player_name, player_color, message)
        VALUES (%s,%s,%s,%s)
    """, (uid, name, color, text), commit=True)

    # detect mentions
    mentions = re.findall(MENTION_REGEX, text)

    msg = {
        "id": msg_id,
        "uid": uid,
        "name": name,
        "color": color,
        "text": text,
        "timestamp": datetime.now().strftime("%H:%M"),
        "mentions": mentions,
        "deleted": 0
    }

    # update unread for everyone except sender
    for user_id in connected_clients.keys():
        if user_id != uid:
            execute("""
                INSERT INTO chat_unread(user_id, unread_count)
                VALUES (%s,1)
                ON DUPLICATE KEY UPDATE unread_count = unread_count + 1
            """, (user_id,), commit=True)

    await broadcast_to_all({
        "action": "new_message",
        "message": msg
    })

    # notify mentions
    for m in mentions:
        await broadcast_to_all({
            "action": "mention",
            "from": name,
            "to": m,
            "message": text
        })

async def send_chat_history(ws):
    rows = execute("""
        SELECT id, player_id, player_name, player_color, message, deleted, created_at
        FROM daily_chat
        WHERE DATE(created_at) = CURDATE()
        ORDER BY id ASC
    """, fetch=True, dictionary=True) or []

    messages = []
    for r in rows:
        created_at = r["created_at"]
        if isinstance(created_at, str):
            time_str = created_at[11:16]
        else:
            time_str = created_at.strftime("%H:%M")

        messages.append({
            "id": r["id"],
            "uid": r["player_id"],
            "name": r["player_name"],
            "color": r["player_color"],
            "text": r["message"],
            "deleted": r.get("deleted", 0),
            "timestamp": time_str
        })

    await ws.send_text(json.dumps({
        "action": "init_chat",
        "messages": messages
    }))

async def handle_delete_message(uid: str, data: dict):

    message_id = data.get("message_id")

    if not message_id:
        return

    row = execute(
        """
        SELECT player_id
        FROM daily_chat
        WHERE id=%s
        """,
        (message_id,),
        fetch=True,
        dictionary=True
    )

    if not row:
        return

    # only owner can delete
    if str(row[0]["player_id"]) != str(uid):
        return

    execute(
        """
        UPDATE daily_chat
        SET deleted=1
        WHERE id=%s
        """,
        (message_id,),
        commit=True
    )

    await broadcast_to_all({
        "action": "message_deleted",
        "message_id": message_id
    })


async def handle_restore_message(uid: str, data: dict):

    message_id = data.get("message_id")

    if not message_id:
        return

    row = execute(
        """
        SELECT player_id
        FROM daily_chat
        WHERE id=%s
        """,
        (message_id,),
        fetch=True,
        dictionary=True
    )

    if not row:
        return

    if str(row[0]["player_id"]) != str(uid):
        return

    execute(
        """
        UPDATE daily_chat
        SET deleted=0
        WHERE id=%s
        """,
        (message_id,),
        commit=True
    )

    await broadcast_to_all({
        "action": "message_restored",
        "message_id": message_id
    })

async def mark_seen(uid: str):

    row = fetch_one(
        """
        SELECT MAX(id) AS last_id
        FROM daily_chat
        """
    )

    if not row:
        return

    last_id = row.get("last_id")

    if last_id is None:
        return

    execute(
        """
        UPDATE chat_unread
        SET last_seen=%s
        WHERE user_id=%s
        """,
        (
            last_id,
            uid
        ),
        commit=True
    )

async def handle_get_rooms(ws: WebSocket, uid: str, name: str, data: dict):
    await ws.send_text(json.dumps({
        "action": "rooms_update",
        "rooms": get_rooms_data()
    }))  

async def handle_ws_action(ws: WebSocket, player_id: str, player_name: str, data: dict):
    """Route WebSocket actions to appropriate handlers."""
    action = data.get("action")
    uid = player_id
    name = player_name
    
    logger.info("WS action=%s from=%s", action, uid)
    
    handler = ACTION_HANDLERS.get(action)

    if handler:
        await handler(ws, uid, name, data)
    else:
        await ws.send_text(json.dumps({"action": "error", "message": f"Unknown action: {action}"}))


# ---------- Scheduled Tasks ----------
async def run_daily_cleanup():
    execute("DELETE FROM players WHERE created_at < CURDATE()", commit=True)
    execute("DELETE FROM daily_chat WHERE created_at < CURDATE()", commit=True)
    execute("DELETE FROM chat_reads", commit=True)
    execute("DELETE FROM chat_unread", commit=True)

    rooms_state.clear()

    await broadcast_to_all({
        "action": "chat_reset"
    })


async def daily_player_cleanup():
    while True:
        now = datetime.now()
        next_run = (
            now + timedelta(days=1)
        ).replace(hour=0, minute=0, second=0, microsecond=0)

        await asyncio.sleep((next_run - now).total_seconds())

        try:
            await run_daily_cleanup()
        except Exception:
            logger.exception(...)

# ---------- Startup ----------
@app.on_event("startup")
def startup():
    """Initialize server state from database."""
    asyncio.create_task(daily_player_cleanup())
    
    logger.info("Loading rooms from DB...")
    try:
        rows = execute("SELECT * FROM rooms", fetch=True, dictionary=True) or []
        for r in rows:
            room_id = str(r["id"])
            players = execute(
                "SELECT id, name, room_id, joined_at, color FROM players WHERE room_id=%s",
                (r["id"],), fetch=True, dictionary=True
            ) or []
            
            rooms_state[room_id] = {
                "host": str(r["host_id"]) if r.get("host_id") else None,
                "players": [{"id": str(p["id"]), "name": p["name"], "color": p.get("color")} for p in players],
                "watchers": [],
                "option": "asc",
                "game_started": bool(r.get("started")),
                "bubbles": {},
                "index": 0,
                "play_order": [],
                "display_order": []
            }
        logger.info("Recovered %d rooms from DB", len(rooms_state))
    except Exception as e:
        logger.exception("Failed to load rooms from DB: %s", e)

# ---------- REST Endpoints ----------
@app.post("/login")
def login(payload: dict = Body(...)):

    name = payload.get("user_name") or payload.get("name")

    if not name:
        raise HTTPException(
            status_code=400,
            detail="user_name required"
        )

    try:
        players = execute(
            "SELECT id, name, color FROM players",
            fetch=True,
            dictionary=True
        ) or []


        if len(players) >= 12:
            raise HTTPException(
                status_code=400,
                detail="Maximum 12 players allowed"
            )


        used_colors = {
            p["color"]
            for p in players
            if p.get("color")
        }


        available_colors = [
            c for c in PLAYER_COLORS
            if c not in used_colors
        ]


        if not available_colors:
            raise HTTPException(
                status_code=400,
                detail="No colors available"
            )


        color = available_colors[0]


        user_id = execute(
            """
            INSERT INTO players
            (name, joined_at, color)
            VALUES (%s, NOW(), %s)
            """,
            (name, color),
            commit=True,
        )


        token = create_access_token(
            {
                "user_id": str(user_id),
                "userName": name,
                "color": color
            }
        )


        return {
            "status": "ok",
            "user_id": str(user_id),
            "userName": name,
            "color": color,
            "token": token,
        }


    except HTTPException:
        raise


    except Exception as e:
        logger.exception(
            "Login failed: %s",
            e
        )

        raise HTTPException(
            status_code=500,
            detail="db error"
        )

@app.post("/logout")
def logout(background_tasks: BackgroundTasks, payload: dict = Body(...)):
    uid = payload.get("user_id") or payload.get("player_id")
    if not uid or uid == "undefined":
        logger.error("Invalid logout uid received: %s", uid)
        raise HTTPException(status_code=400, detail="user_id required")

    try:
        execute("DELETE FROM players WHERE id=%s", (uid,), commit=True)

        if uid in connected_clients:
            connected_clients.pop(uid, None)

        # Remove from all rooms
        for rid in list(rooms_state.keys()):
            room = rooms_state[rid]
            room["players"] = [p for p in room["players"] if p["id"] != uid]
            room["watchers"] = [w for w in room.get("watchers", []) if str(w["id"]) != str(uid)]

        background_tasks.add_task(broadcast_rooms)
        return {"status": "logged_out", "userId": uid}
    except HTTPException:
        raise

    except Exception as e:
        logger.exception("Logout failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="db error"
        )

@app.get("/rooms")
def list_rooms():
    try:
        return execute(
            """SELECT r.id, r.host_id, r.created_at, COUNT(p.id) AS player_count
               FROM rooms r LEFT JOIN players p ON r.id=p.room_id
               GROUP BY r.id""",
            fetch=True, dictionary=True
        ) or []
    except Exception as e:
        logger.exception("Failed to list rooms: %s", e)
        raise HTTPException(status_code=500, detail="db error")

# ---------- WebSocket Endpoint ----------
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    query = ws.query_params
    token = query.get("token")

    if not token:
        await ws.close(code=1008)
        return

    payload = verify_token(token)
    if not payload:
        await ws.close(code=1008)
        return

    player_id = norm_id(payload["user_id"])
    player_name = payload["userName"]
    player_color = payload.get("color")

    
    await ws.accept()
    connected_clients[player_id] = ws
    ws.scope["player_id"] = player_id
    await broadcast_online_users()
    await mark_seen(player_id)
    await broadcast_rooms()
    
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except Exception:
                logger.error("Invalid WS message: %s", raw)
                continue

            await handle_ws_action(ws, player_id, player_name, msg)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: %s", player_id)

    except Exception as e:
        logger.exception("WebSocket crashed unexpectedly: %s", e)

    finally:

        try:
            typing_users.pop(player_id, None)

            # only remove if same websocket
            if connected_clients.get(player_id) == ws:
                connected_clients.pop(player_id, None)
            await broadcast_typing(
                "typing_stop",
                player_id,
                player_name
            )

        except Exception:
            logger.exception("cleanup failed")

        for rid, room in list(rooms_state.items()):

            if str(room.get("host")) == str(player_id):

                await close_room(
                    rid,
                    "Host disconnected"
                )
                break

        await broadcast_online_users()
        await broadcast_rooms()
