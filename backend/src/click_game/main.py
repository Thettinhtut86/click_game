import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from click_game.api.routers import auth, health, rooms
from click_game.core.config import settings
from click_game.core.logging import configure_logging
from click_game.db.database import close_database, initialize_database
from click_game.services.cleanup_service import daily_cleanup_loop
from click_game.state.rooms import room_store
from click_game.websocket.endpoint import router as websocket_router
from click_game.websocket.manager import websocket_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    initialize_database()
    room_store.load_from_database()

    cleanup_task = asyncio.create_task(daily_cleanup_loop())

    yield

    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

    await websocket_manager.close_all()
    close_database()


app = FastAPI(title="Click Game API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(rooms.router)
app.include_router(websocket_router)
