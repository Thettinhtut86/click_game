# Click Game Backend

FastAPI backend for the realtime multiplayer Click Game.

## Structure

- `src/click_game/api` — REST endpoints
- `src/click_game/core` — configuration, security, logging
- `src/click_game/db` — database access
- `src/click_game/services` — business logic
- `src/click_game/state` — process-local realtime state
- `src/click_game/websocket` — WebSocket endpoint, dispatcher and handlers
- `src/click_game/schemas` — request/response validation
- `tests` — unit/integration/WebSocket tests

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn click_game.main:app --reload
```

For the current in-memory WebSocket architecture, run one application worker. Multiple workers require shared state/pub-sub such as Redis.

## Compatibility

The WebSocket action names and JSON field names are kept compatible with the supplied `server.py`.
