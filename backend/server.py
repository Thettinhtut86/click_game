# server.py
import json
import logging
import asyncio
import random
import mysql.connector
from mysql.connector import Error
from fastapi import BackgroundTasks, FastAPI, WebSocket, WebSocketDisconnect, Body
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from typing import Dict, Optional

# ---------- Configuration ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("bubble-game")

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "live_game"
}

PLAYER_COLORS = [
    "#e6194b", "#3cb44b", "#ffe119", "#437fd8",
    "#f58231", "#440568", "#46f0f0", "#f032e6",
    "#1d0a0a", "#fabebe", "#008080", "#2600ff"
]

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

# ---------- Database Helper ----------
def execute(query: str, params: tuple = None, fetch: bool = False, dictionary: bool = False, commit: bool = False):
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
            return cursor.fetchall()
    except Error as e:
        logger.error("DB Error: %s", e)
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def serialize_player(p: dict) -> dict:
    return {
        "id": str(p["id"]),
        "name": p.get("name"),
        "color": p.get("color")
    }            

# ---------- Utility Functions ----------
def norm_id(x) -> str:
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
    
    for player in room["players"]:
        ws = connected_clients.get(str(player["id"]))
        if ws:
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                pass
    
    # Also broadcast to watchers
    for watcher in room.get("watchers", []):
        ws = connected_clients.get(str(watcher["id"]))
        if ws:
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                pass

async def broadcast_rooms():
    """Broadcast room list update to all clients."""
    try:
        rooms = execute(
            """SELECT r.id, r.host_id, r.created_at, COUNT(p.id) AS player_count
               FROM rooms r LEFT JOIN players p ON r.id = p.room_id
               GROUP BY r.id""",
            fetch=True, dictionary=True
        ) or []
    except Exception as e:
        logger.exception("Failed to fetch rooms: %s", e)
        rooms = []
    
    await broadcast_to_all({"action": "rooms_update", "rooms": rooms})

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
            "players": [player_info],
            "option": data.get("option", "asc")
        })
        
        await ws.send_text(json.dumps({
            "action": "room_created",
            "roomId": room_id,
            "hostId": uid
        }))
        
        await broadcast_rooms()
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
    """Handle starting a game."""
    room_id = str(data.get("roomId"))
    
    if not room_id:
        await ws.send_text(json.dumps({"action": "error", "message": "roomId required"}))
        return
    
    room = rooms_state.get(room_id)
    if not room:
        await ws.send_text(json.dumps({"action": "error", "message": "Room not found"}))
        return
    
    # Only host can start game
    if str(uid) != str(room.get("host")):
        await ws.send_text(json.dumps({"action": "error", "message": "Only host can start the game"}))
        return
    
    # Generate bubble order
    displayOrder = generate_bubble_order()

    if room.get("option") == "desc":
        play_order = list(range(100, 0, -1))
    else:
        play_order = list(range(1, 101))
    room["play_order"] = play_order
    room["display_order"] = displayOrder
    room["index"] = 0
    room["game_started"] = True
    room["bubbles"] = {f"B{i}": None for i in displayOrder}

    # Update database
    try:
        execute("UPDATE rooms SET started=1 WHERE id=%s", (room_id,), commit=True)
    except Exception:
        logger.exception("Failed to update room started status")
    
    await broadcast_to_room(room_id, {
        "action": "game_started",
        "roomId": room_id,
        "bubbles": room["bubbles"],
        "players": room["players"],
        "play_order": room["play_order"],
        "display_order": room["display_order"],
        "option": room["option"]
    })

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

async def handle_ws_action(ws: WebSocket, player_id: str, player_name: str, data: dict):
    """Route WebSocket actions to appropriate handlers."""
    action = data.get("action")
    uid = data.get("uid") or player_id
    name = data.get("name") or player_name
    
    logger.info("WS action=%s from=%s", action, uid)
    
    if action == "handshake":
        await handle_handshake(ws, uid, name)
    elif action == "create_room":
        await handle_create_room(ws, uid, name, data)
    elif action == "join_room":
        await handle_join_room(ws, uid, name, data)
    elif action == "leave_room":
        await handle_leave_room(ws, uid, data)
    elif action == "start_game":
        await handle_start_game(ws, uid, data)
    elif action == "quit_room":
        await handle_quit_room(ws, uid, data)
    elif action == "select_bubble":
        await handle_select_bubble(ws, uid, data)
    else:
        await ws.send_text(json.dumps({"action": "error", "message": f"Unknown action: {action}"}))

# ---------- Scheduled Tasks ----------
async def daily_player_cleanup():
    """Clear player records daily at midnight."""
    while True:
        now = datetime.now()
        next_run = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        wait_time = (next_run - now).total_seconds()
        await asyncio.sleep(wait_time)
        
        logger.info("Daily cleanup: Clearing all players from DB...")
        try:
            execute("DELETE FROM players", commit=True)
            rooms_state.clear()
        except Exception as e:
            logger.exception("Daily cleanup failed: %s", e)

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
        return {"status": "error", "message": "user_name required"}
    
    try:
        players = execute("SELECT id, name, color FROM players", fetch=True, dictionary=True) or []
        if len(players) >= 12:
            return {"status": "error", "message": "Maximum 12 players allowed"}
        
        used_colors = {p["color"] for p in players if p.get("color")}
        available_colors = [c for c in PLAYER_COLORS if c not in used_colors]
        if not available_colors:
            return {"status": "error", "message": "No colors available"}
        
        color = available_colors[0]
        execute("INSERT INTO players (name, joined_at, color) VALUES (%s, NOW(), %s)", (name, color), commit=True)
        row = execute("SELECT LAST_INSERT_ID() AS id", fetch=True, dictionary=True)[0]
        
        return {"status": "ok", "userId": str(row["id"]), "userName": name, "color": color}
    except Exception as e:
        logger.exception("Login failed: %s", e)
        return {"status": "error", "message": "db error"}

@app.post("/logout")
def logout(background_tasks: BackgroundTasks, payload: dict = Body(...)):
    uid = payload.get("user_id") or payload.get("player_id")
    if not uid:
        return {"status": "error", "message": "user_id required"}
    
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
    except Exception as e:
        logger.exception("Logout failed: %s", e)
        return {"status": "error", "message": "db error"}

@app.post("/rooms/create")
def create_room(payload: dict = Body(...)):
    try:
        uid = norm_id(payload["user_id"])
        room_id = str(execute(
            "INSERT INTO rooms (host_id, created_at) VALUES (%s, NOW())",
            (uid,), commit=True
        ))
        
        execute("UPDATE players SET room_id=%s WHERE id=%s", (room_id, uid), commit=True)
        player_row = execute(
            "SELECT id, name, color FROM players WHERE id=%s",
            (uid,), fetch=True, dictionary=True
        )
        option = payload.get("option", "asc")
        rooms_state[room_id] = ensure_room({
            "host": uid,
            "option": option,
            "players": [
                {
                    "id": uid,
                    "name": player_row[0]["name"] if player_row else "Unknown",
                    "color": player_row[0]["color"] if player_row else None
                }
            ],
        })
        
        return {"room_id": room_id}
    except Exception as e:
        logger.exception(e)
        return {"error": "create_room_failed"}

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
        return []

@app.get("/rooms/{room_id}")
def get_room(room_id: int):
    try:
        room = execute("SELECT id, host_id, created_at FROM rooms WHERE id=%s", (room_id,), fetch=True, dictionary=True)
        if not room:
            return {"status": "error", "message": "room not found"}
        
        players = execute("SELECT id, name FROM players WHERE room_id=%s", (room_id,), fetch=True, dictionary=True) or []
        return {"id": room_id, "host_id": room[0]["host_id"], "players": players}
    except Exception as e:
        logger.exception("Failed to get room: %s", e)
        return {"status": "error", "message": "db error"}

@app.get("/players/{name}")
def get_player_by_name(name: str):
    try:
        row = execute(
            "SELECT id, name FROM players WHERE name=%s ORDER BY joined_at DESC LIMIT 1",
            (name,), fetch=True, dictionary=True
        )
        return row[0] if row else {"status": "error", "message": "player not found"}
    except Exception as e:
        logger.exception("Failed to fetch player: %s", e)
        return {"status": "error", "message": "db error"}

# ---------- WebSocket Endpoint ----------
@app.websocket("/ws/{player_name}")
async def websocket_endpoint(ws: WebSocket, player_name: str):
    # Get or create player
    rows = execute(
        "SELECT id FROM players WHERE name=%s ORDER BY joined_at DESC LIMIT 1",
        (player_name,), fetch=True, dictionary=True
    )
    
    if rows:
        player_id = norm_id(rows[0]["id"])
    else:
        player_id = norm_id(execute(
            "INSERT INTO players (name, joined_at) VALUES (%s, NOW())",
            (player_name,), commit=True
        ))
    
    await ws.accept()
    connected_clients[player_id] = ws
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
        await asyncio.sleep(5)
        if connected_clients.get(player_id) is ws:
            try:
                connected_clients.pop(player_id, None)
            except Exception:
                logger.exception("cleanup failed")
            await broadcast_rooms()