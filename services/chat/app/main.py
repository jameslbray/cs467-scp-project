# services/chat/app/main.py

import socketio
from fastapi import FastAPI
from app.core.config import settings
from app.db.mongo import init_mongo
from app.db.session import init_sql

# 1. Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.CORS_ORIGINS,
)
app = FastAPI()
# 2. Mount Socket.IO under a path
app.mount("/ws", socketio.ASGIApp(sio, other_asgi_app=app))


@app.on_event("startup")
async def startup():
    init_mongo()
    await init_sql()
    # any other startup tasks

# 3. Define your Socket.IO event handlers


@sio.event
async def connect(sid, environ):
    # authenticate via JWT, etc.
    ...


@sio.event
async def send_message(sid, data):
    # save to PostgreSQL/MongoDB, publish to RabbitMQ, then emit…
    await sio.emit("receive_message", data, room=data["room_id"])
