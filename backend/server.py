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
from typing import Dict


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("bubble-game")

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "live_game"   # adjust DB name
}

PLAYER_COLORS = [
    "#e6194b", "#3cb44b", "#ffe119", "#437fd8",
    "#f58231", "#440568", "#46f0f0", "#f032e6",
    "#1d0a0a", "#fabebe", "#008080", "#2600ff"
]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory state
rooms_state: Dict[str, dict] = {}  # roomId -> { host, players: [{id,name,color}], option, game_started, bubbles }
connected_clients: Dict[str, WebSocket] = {}  # player_id -> websocket

# ---------- DB helper ----------
def execute(query: str, params: tuple = None, fetch: bool = False, dictionary: bool = False, commit: bool = False):
    conn = None
    cursor = None
    result = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=dictionary)
        cursor.execute(query, params or ())
        if commit:
            conn.commit()
        if fetch:
            return cursor.fetchall()
        elif commit:
            conn.commit()
            result = cursor.lastrowid
    except Error as e:
        logger.error("DB Error: %s", e)
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return result

# ---------- Startup: load rooms from DB ----------
@app.on_event("startup")
def load_rooms_from_db():
    asyncio.create_task(clear_players_daily())
    logger.info("Loading rooms from DB...")
    try:
        rows = execute("SELECT * FROM rooms", fetch=True, dictionary=True) or []
        for r in rows:
            room_id = str(r["id"])
            players = execute(
                "SELECT id, name, room_id, joined_at FROM players WHERE room_id=%s",
                (r["id"],), fetch=True, dictionary=True
            ) or []
            players_slim = [{"id": str(p["id"]), "name": p["name"], "color": None} for p in players]
            rooms_state[room_id] = {
                "host": str(r["host_id"]) if r.get("host_id") is not None else None,
                "players": players_slim,
                "option": "asc",
                "game_started": bool(r.get("started")),
                "bubbles": {}
            }
        logger.info("Recovered %d rooms from DB", len(rooms_state))
    except Exception as e:
        logger.exception("Failed to load rooms from DB: %s", e)


# ---------- Broadcast helpers ----------
async def broadcast_menu():
    # Send connected users to components that listen for menu_update
    users = []
    for uid in connected_clients.keys():
        # We don't have persistent color in DB (frontend keeps color). Send minimal info.
        users.append({"id": uid, "name": "Player"})
    payload = {"action": "menu_update", "users": users}
    for ws in list(connected_clients.values()):
        try:
            await ws.send_text(json.dumps(payload))
        except Exception:
            pass

async def broadcast_rooms():
    # read canonical rooms from DB (so REST/WS writes are authoritative)
    try:
        rooms = execute(
            """
            SELECT r.id, r.host_id, r.created_at, COUNT(p.id) AS player_count
            FROM rooms r
            LEFT JOIN players p ON r.id = p.room_id
            GROUP BY r.id
            """,
            fetch=True, dictionary=True
        ) or []
    except Exception as e:
        logger.exception("broadcast_rooms DB read failed: %s", e)
        rooms = []
    payload = {"action": "rooms_update", "rooms": rooms}
    for ws in list(connected_clients.values()):
        try:
            await ws.send_text(json.dumps(payload))
        except Exception:
            pass

async def broadcast_room_update(room_id: str):
    state = rooms_state.get(str(room_id))
    if not state:
        return
    payload = {
        "action": "room_update",
        "roomId": str(room_id),
        "players": state["players"],
        "watchers": state.get("watchers", []),
        "hostId": state["host"]
    }
    for pid, ws in list(connected_clients.items()):
        try:
            await ws.send_text(json.dumps(payload))
        except Exception:
            pass


# ---------- REST endpoints----------
@app.post("/login")
def login(payload: dict = Body(...)):
    name = payload.get("user_name") or payload.get("name")
    if not name:
        return {"status": "error", "message": "user_name required"}

    try:
        # Wrap everything that can fail
        players = execute("SELECT id, name, color FROM players", fetch=True, dictionary=True) or []
        if len(players) >= 12:
            return {"status": "error", "message": "Maximum 12 players allowed"}

        used_colors = {p["color"] for p in players if p.get("color")}
        available_colors = [c for c in PLAYER_COLORS if c not in used_colors]
        if not available_colors:
            return {"status": "error", "message": "No colors available"}
        color = available_colors[0]

        # create player and return id
        execute(
            "INSERT INTO players (name, joined_at, color) VALUES (%s, NOW(), %s)",
            (name, color),
            commit=True
        )
        row = execute("SELECT LAST_INSERT_ID() AS id", fetch=True, dictionary=True)[0]
        player_id = int(row["id"])
        return {"status": "ok", "userId": str(player_id), "userName": name, "color": color}

    except Exception as e:
        logger.exception("Login failed: %s", e)
        return {"status": "error", "message": "db error"}

@app.post("/logout")
def logout(background_tasks: BackgroundTasks, payload: dict = Body(...)):
    # frontend sends { user_id }
    uid = payload.get("user_id") or payload.get("player_id")
    if not uid:
        return {"status": "error", "message": "user_id required"}
    try:
        # remove player record (your frontend expected this behavior)
        execute("DELETE FROM players WHERE id=%s", (uid,), commit=True)
        # also cleanup connected_clients if present
        if uid in connected_clients:
            # we won't close socket here; client typically disconnects
            connected_clients.pop(uid, None)
        # update rooms_state to remove player
        for rid in list(rooms_state.keys()):
            rooms_state[rid]["players"] = [p for p in rooms_state[rid]["players"] if p["id"] != uid]
        # async broadcast rooms/menu
        background_tasks.add_task(broadcast_rooms)
        background_tasks.add_task(broadcast_menu)
        return {"status": "logged_out", "userId": uid}
    except Exception as e:
        logger.exception("Logout failed: %s", e)
        return {"status": "error", "message": "db error"}

@app.post("/rooms/create")
def create_room(background_tasks: BackgroundTasks, payload: dict = Body(...)):
    uname = payload.get("user_name")
    if not uname:
        return {"status": "error", "message": "user_name required"}

    try:
        # 1. Find player by name
        existing = execute(
            "SELECT id FROM players WHERE name=%s ORDER BY joined_at DESC LIMIT 1",
            (uname,),
            fetch=True,
            dictionary=True
        )

        if existing:
            uid = existing[0]["id"]
        else:
            # auto-create player if missing
            uid = execute("INSERT INTO players (name, joined_at) VALUES (%s, NOW())", (uname,), commit=True)  
            

        # 2. Create room
        room_id = execute(
            "INSERT INTO rooms (host_id, created_at) VALUES (%s, NOW())",
            (uid,),
            commit=True
        )
        print("room id: ", room_id)

        # 3. Update player's room_id
        execute("UPDATE players SET room_id=%s WHERE id=%s", (room_id, uid), commit=True)

        # 4. Update in-memory state
        rooms_state[str(room_id)] = {
            "host": str(uid),
            "players": [{"id": str(uid), "name": uname, "color": None}],
            "watchers": [],
            "option": "asc",
            "game_started": False,
            "bubbles": {}
        }

        # 5. Schedule async broadcasts safely
        background_tasks.add_task(broadcast_rooms)
        background_tasks.add_task(broadcast_room_update, str(room_id))

        return {"status": "created", "room_id": room_id, "uid": uid}

    except Exception as e:
        logger.exception("create_room failed: %s", e)
        return {"status": "error", "message": "db error"}

@app.get("/rooms")
def list_rooms():
    try:
        rooms = execute(
            "SELECT r.id, r.host_id, r.created_at, COUNT(p.id) AS player_count "
            "FROM rooms r LEFT JOIN players p ON r.id=p.room_id GROUP BY r.id",
            fetch=True, dictionary=True
        ) or []
        # convert ids to native types or strings as your frontend expects numbers; keep as is
        return rooms
    except Exception as e:
        logger.exception("list_rooms failed: %s", e)
        return []

@app.get("/rooms/{room_id}")
def get_room(room_id: int):
    try:
        room = execute(
            "SELECT r.id, r.host_id, r.created_at FROM rooms r WHERE r.id=%s",
            (room_id,), fetch=True, dictionary=True
        )
        if not room:
            return {"status": "error", "message": "room not found"}
        players = execute("SELECT id, name FROM players WHERE room_id=%s", (room_id,), fetch=True, dictionary=True) or []
        return {"id": room_id, "host_id": room[0]["host_id"], "players": players}
    except Exception as e:
        logger.exception("get_room failed: %s", e)
        return {"status": "error", "message": "db error"}
    
@app.get("/players/{name}")
def get_player_by_name(name: str):
    try:
        row = execute(
            "SELECT id, name FROM players WHERE name=%s ORDER BY joined_at DESC LIMIT 1",
            (name,),
            fetch=True,
            dictionary=True
        )
        if row:
            return row[0]
        return {"status": "error", "message": "player not found"}
    except Exception as e:
        logger.exception("Failed to fetch player by name: %s", e)
        return {"status": "error", "message": "db error"}

# ---------- WebSocket endpoint ----------
class CloseCodes:
    INVALID_PLAYER = 4000

@app.websocket("/ws/{player_name}")
async def websocket_endpoint(websocket: WebSocket, player_name: str):
    try:
        rows = execute(
            "SELECT id, name FROM players WHERE name=%s ORDER BY joined_at DESC LIMIT 1",
            (player_name,),
            fetch=True,
            dictionary=True
        )
        if not rows:
            execute("INSERT INTO players (name, joined_at) VALUES (%s, NOW())", (player_name,), commit=True)
            row = execute("SELECT LAST_INSERT_ID() AS id", fetch=True, dictionary=True)[0]
            player_id = str(row["id"])
            logger.info(f"Auto-created player {player_name} with id {player_id}")
            color = None
        else:
            player_id = str(rows[0]["id"])
            color = rows[0].get("color")
    except Exception as e:
        logger.error(f"DB error on WebSocket connect: {e}")
        player_id = f"temp_{random.randint(1000,9999)}"

    await websocket.accept()
    connected_clients[player_id] = websocket
    logger.info("WS CONNECT: %s (%s)", player_name, player_id)
    asyncio.create_task(broadcast_menu())
    asyncio.create_task(broadcast_rooms())

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except Exception:
                logger.warning("Invalid JSON from %s: %s", player_id, raw)
                continue
            await handle_ws_action(websocket, player_id, player_name, color, msg)
    except WebSocketDisconnect:
        logger.info("WS Disconnect: %s", player_id)
        connected_clients.pop(player_id, None)
        await remove_player_from_all_rooms(player_id)
        asyncio.create_task(broadcast_menu())
        asyncio.create_task(broadcast_rooms())


# ---------- WS action handler ----------
async def handle_ws_action(ws: WebSocket, pid: str, pname: str, color: str, data: dict):
    action = data.get("action")
    # tolerate both roomId and room_id
    room_id = data.get("roomId") or data.get("room_id")
    # some messages include uid/name fields; prefer path params
    uid = data.get("uid") or pid
    name = data.get("name") or pname

    logger.info("WS action=%s from=%s", action, uid)

    # handshake -> ack
    if action == "handshake":
        payload = {"action": "handshake_ack", "status": "connected", "userId": uid, "userName": name}
        await ws.send_text(json.dumps(payload))
        return

    # create_room -> frontend sends roomId after REST; but support WS-only creation too
    if action == "create_room":
        
        rid = room_id
        if not rid:
            await ws.send_text(json.dumps({
                "action": "error",
                "message": "Missing roomId — create via API first."
            }))
            return

        rid = str(rid)
        # Ensure in-memory state exists
        if rid not in rooms_state:
            players = execute("SELECT id, name FROM players WHERE room_id=%s", (rid,), fetch=True, dictionary=True) or []
            rooms_state[rid] = {
                "host": str(uid),
                "players": [{"id": str(p["id"]), "name": p["name"], "color": None} for p in players],
                "option": data.get("option", "asc"),
                "game_started": False,
                "bubbles": {}
            }
        # Broadcast only
        asyncio.create_task(broadcast_rooms())
        asyncio.create_task(broadcast_room_update(rid))

        return

    # join_room
    if action == "join_room":
        if not room_id:
            await ws.send_text(json.dumps({
                "action": "error",
                "message": "roomId required"
            }))
            return

        rid = str(room_id)

        # Check if game already started before joining
        if rid in rooms_state and rooms_state[rid].get("game_started"):
            await ws.send_text(json.dumps({
                "action": "error",
                "message": "Game already started, cannot join"
            }))
            return

        if rid not in rooms_state:
            # load from DB if exists
            r = execute("SELECT id, host_id FROM rooms WHERE id=%s", (rid,), fetch=True, dictionary=True)
            if not r:
                await ws.send_text(json.dumps({"action": "error", "message": "Room not available"}))
                return
            # populate from DB
            players = execute("SELECT id, name FROM players WHERE room_id=%s", (rid,), fetch=True, dictionary=True) or []
            rooms_state[rid] = {
                "host": str(r[0]["host_id"]) if r[0].get("host_id") else None,
                "players": [{"id": str(p["id"]), "name": p["name"], "color": None} for p in players],
                "option": "asc",
                "game_started": False,
                "bubbles": {}
            }

        # Check capacity (max 4)
        if len(rooms_state[rid]["players"]) >= 4:
        # Add as watcher instead of rejecting
            rooms_state[rid]["watchers"].append({"id": uid, "name": name})
            await ws.send_text(json.dumps({
                "action": "joined_as_watcher",
                "roomId": rid,
                "message": "Room full — you are watching"
            }))
            # Still update UI for all users
            await broadcast_room_update(rid)
            asyncio.create_task(broadcast_rooms())
            return

        # persist player's room_id
        try:
            execute("UPDATE players SET room_id=%s WHERE id=%s", (rid, uid), commit=True)
        except Exception:
            logger.exception("Failed to update player's room_id")

        # add to memory if not present
        if not any(p["id"] == uid for p in rooms_state[rid]["players"]):
            rooms_state[rid]["players"].append({"id": uid, "name": name, "color": None})

        # broadcast room update to players in that room
        await broadcast_room_update(rid)
        asyncio.create_task(broadcast_rooms())
        return

    # leave_room
    if action == "leave_room":
        if not room_id:
            await ws.send_text(json.dumps({
                "action": "error",
                "message": "roomId required"
            }))
            return

        rid = str(room_id)

        # Ignore leave requests if game already started
        if rid in rooms_state and rooms_state[rid].get("game_started", False):
            logger.info(f"Leave ignored for player {uid} in started room {rid}")
            await ws.send_text(json.dumps({
                "action": "leave_ignored",
                "reason": "game_started"
            }))
            return

        # normal leave flow
        if rid in rooms_state:
            rooms_state[rid]["players"] = [
                p for p in rooms_state[rid]["players"] if p["id"] != uid
            ]

        # persist: clear player's room_id
        try:
            execute("UPDATE players SET room_id=NULL WHERE id=%s", (uid,), commit=True)
        except Exception:
            logger.exception("Failed to clear player's room_id")

        # if room empty -> delete
        if rid in rooms_state and len(rooms_state[rid]["players"]) == 0:
            try:
                execute("DELETE FROM rooms WHERE id=%s", (rid,), commit=True)
                execute("DELETE FROM players WHERE room_id=%s", (rid,), commit=True)
            except Exception:
                logger.exception("Failed to delete empty room from DB")
            rooms_state.pop(rid, None)
        else:
            asyncio.create_task(broadcast_room_update(rid))

        asyncio.create_task(broadcast_rooms())
        return


    # start_game
    if action == "start_game":
        if not room_id:
            await ws.send_text(json.dumps({"action": "error", "message": "roomId required"}))
            return
            
        rid = str(room_id)
        if rid not in rooms_state:
            await ws.send_text(json.dumps({"action": "error", "message": "Room not found"}))
            return

        # only host can start
        if rooms_state[rid].get("host") != uid:
            await ws.send_text(json.dumps({"action": "error", "message": "Only host can start"}))
            return
            
        option = rooms_state[rid].get("option", "asc")

        display_numbers = list(range(1, 101))
        random.shuffle(display_numbers)

        play_order = list(range(1, 101)) if option == "asc" else list(range(100, 0, -1))
        # Initialize bubbles with proper structure
        bubbles = {}
        for i in display_numbers:
            bubbles[f"B{i}"] = None  # Store as null initially
        
        rooms_state[rid]["bubbles"] = bubbles
        rooms_state[rid]["display_order"] = display_numbers
        rooms_state[rid]["play_order"] = play_order         
        rooms_state[rid]["index"] = 0
        rooms_state[rid]["game_started"] = True  # Add this flag

        # notify players
        payload = {
            "action": "game_started",
            "roomId": rid,
            "bubbles": bubbles,
            "players": rooms_state[rid]["players"],
            "option": option,
            "display_order": display_numbers,
            "play_order": play_order
        }

        for p in rooms_state[rid]["players"]:
            if not p.get("color"):
                # assign default color if missing
                used_colors = {pl.get("color") for pl in rooms_state[rid]["players"] if pl.get("color")}
                available_colors = [c for c in PLAYER_COLORS if c not in used_colors]
                p["color"] = available_colors[0] if available_colors else "#000000"
                execute("UPDATE players SET color=%s WHERE id=%s", (p["color"], p["id"]), commit=True)
            ws_target = connected_clients.get(str(p["id"]))
            if ws_target:
                try:
                    await ws_target.send_text(json.dumps(payload))
                except Exception:
                    pass

        execute("UPDATE rooms SET started=1 WHERE id=%s", (rid,), commit=True)
        asyncio.create_task(broadcast_rooms())
        return
    
    # quit_room (player quits game manually)
    if action == "quit_room":
        if not room_id:
            await ws.send_text(json.dumps({"action": "error", "message": "roomId required"}))
            return

        rid = str(room_id)
        if rid not in rooms_state:
            await ws.send_text(json.dumps({"action": "error", "message": "Room not found"}))
            return

        players = rooms_state[rid]["players"]
        host_id = rooms_state[rid].get("host")

        # Remove the quitting player from memory
        rooms_state[rid]["players"] = [p for p in players if str(p["id"]) != str(uid)]

        # Clear player's room_id in DB
        try:
            execute("UPDATE players SET room_id=NULL WHERE id=%s", (uid,), commit=True)
        except Exception:
            logger.exception("Failed to clear player's room_id")

        # If host quits, destroy the entire room
        if str(uid) == str(host_id):
            try:
                execute("DELETE FROM rooms WHERE id=%s", (rid,), commit=True)
                execute("UPDATE players SET room_id=NULL WHERE room_id=%s", (rid,), commit=True)
            except Exception:
                logger.exception("Failed to delete room from DB")

            # Notify all players (if still connected)
            all_users = rooms_state[rid]["players"][:] 
            
            payload = {"action": "room_closed", "roomId": rid, "message": "Host has quit. Room closed."}

            for p in all_users:
                ws_target = connected_clients.get(str(p["id"]))
                if ws_target:
                    try:
                        await ws_target.send_text(json.dumps(payload))
                    except Exception:
                        pass

            await ws.send_text(json.dumps(payload))
            
            rooms_state.pop(rid, None)

            # Broadcast updated lobby
            asyncio.create_task(broadcast_rooms())
            return

        # If room still has players, broadcast update
        asyncio.create_task(broadcast_room_update(rid))
        asyncio.create_task(broadcast_rooms())

        # Acknowledge quitter
        await ws.send_text(json.dumps({"action": "quit_ack", "roomId": rid}))
        return

    # select_bubble
    if action == "select_bubble":
        if not room_id or not data.get("bubble_id"):
            await ws.send_text(json.dumps({
                "action": "error",
                "message": "roomId and bubble_id required"
            }))
            return

        rid = str(room_id)
        bid = data.get("bubble_id")

        if rid not in rooms_state or not rooms_state[rid].get("game_started"):
            await ws.send_text(json.dumps({
                "action": "error",
                "message": "Game not started or room not found"
            }))
            return

        room = rooms_state[rid]
        bubbles = room["bubbles"]
        order = room["play_order"] 
        index = room["index"]

        # expected bubble
        expected_label = f"B{order[index]}"
        if bid != expected_label:
            await ws.send_text(json.dumps({
                "action": "error",
                "message": f"You must click {expected_label} next!"
            }))
            return

        # ensure player exists
        player = next((p for p in room["players"] if str(p["id"]) == str(uid)), None)
        if not player:
            # create player object if missing
            player = {"id": uid, "name": name, "color": None}
            room["players"].append(player)

        # assign color if missing
        if not player.get("color"):
                try:
                    row = execute(
                        "SELECT color FROM players WHERE id=%s", 
                        (uid,), fetch=True, dictionary=True
                    )
                    if row and row[0].get("color"):
                        player["color"] = row[0]["color"]
                    else:
                        # fallback color from predefined PLAYER_COLORS
                        used_colors = {p["color"] for p in room["players"] if p.get("color")}
                        available_colors = [c for c in PLAYER_COLORS if c not in used_colors]
                        player["color"] = available_colors[0] if available_colors else "#000000"
                        execute("UPDATE players SET color=%s WHERE id=%s", (player["color"], uid), commit=True)
                except Exception:
                    logger.exception("Failed to fetch or assign player color")
                    player["color"] = "#000000"

        # assign bubble ownership
        bubbles[bid] = {"uid": uid, "color": player["color"]}
        room["index"] += 1

        # broadcast bubble update
        payload = {
            "action": "update_bubbles",
            "roomId": rid,
            "bubbles": bubbles
        }

        for p in room["players"]:
            ws_target = connected_clients.get(str(p["id"]))
            if ws_target:
                try:
                    await ws_target.send_text(json.dumps(payload))
                except Exception:
                    pass

        # end of game check
        if room["index"] >= len(order):
            scores = {}
            for b in bubbles.values():
                if b:
                    pid = b["uid"]
                    scores[pid] = scores.get(pid, 0) + 1
            
            # Find max score
            max_score = max(scores.values()) if scores else 0
            
            # Find all players with max score (handles ties)
            winners = [pid for pid, score in scores.items() if score == max_score]
            
            # Get winner info for all winners
            winner_players = []
            for winner_id in winners:
                winner = next((p for p in room["players"] if str(p["id"]) == str(winner_id)), None)
                if winner:
                    winner_players.append(winner)
            
            payload_end = {
                "action": "end_game",
                "roomId": rid,
                "winners": winner_players,  # Changed from "winner" to "winners" (array)
                "is_tie": len(winners) > 1,  # Add tie flag
                "scores": scores
            }
            
            for p in room["players"]:
                ws_target = connected_clients.get(str(p["id"]))
                if ws_target:
                    try:
                        await ws_target.send_text(json.dumps(payload_end))
                    except Exception:
                        pass
            
            # Handle DB update for tie
            if len(winners) == 1:
                execute("UPDATE rooms SET winner_id=%s, started=0 WHERE id=%s", (winners[0], rid), commit=True)
            else:
                # For tie, you might want to store multiple winners or just mark as tie
                # Option 1: Store as comma-separated IDs
                winner_ids = ",".join(winners)
                execute("UPDATE rooms SET winner_id=%s, started=0 WHERE id=%s", (winner_ids, rid), commit=True)
                # Option 2: Or you could add a 'tie' column to your rooms table
            
            rooms_state.pop(rid, None)
            asyncio.create_task(broadcast_rooms())



    # fallback: unknown action
    await ws.send_text(json.dumps({"action": "error", "message": "Unknown action"}))

handle_ws_message = handle_ws_action

# ---------- Helper to remove player from all rooms ----------
async def remove_player_from_all_rooms(pid: str):
    for rid in list(rooms_state.keys()):
        rooms_state[rid]["players"] = [p for p in rooms_state[rid]["players"] if p["id"] != pid]
        if len(rooms_state[rid]["players"]) == 0:
            try:
                rooms_state.pop(rid, None)
            except Exception:
                logger.exception("Failed to remove empty room from DB")
        else:
            asyncio.create_task(broadcast_room_update(rid))
    try:
        execute("UPDATE players SET room_id=NULL WHERE id=%s", (pid,), commit=True)
    except Exception:
        logger.exception("Failed to clear player's room in DB")

async def clear_players_daily():
    while True:
        now = datetime.now()
        next_run = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        wait_time = (next_run - now).total_seconds()
        await asyncio.sleep(wait_time)
        logger.info("Clearing all players from DB...")
        execute("DELETE FROM players", commit=True)

def calculate_scores(bubbles):
    scores = {}
    for b in bubbles.values():
        if b:
            pid = b["uid"]
            scores[pid] = scores.get(pid, 0) + 1
    return scores