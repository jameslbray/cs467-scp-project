import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router as api_router
from app.socket_events import register_socketio_events

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    # Allow all origins during development,
    # change to specific origin in production
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register REST API routes
app.include_router(api_router)

# Register Socket.IO events
register_socketio_events(sio)

# ASGI app for Uvicorn
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)
