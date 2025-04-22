from fastapi import APIRouter
from typing import Dict, Any
from app.api.chat import router as chat_router
from app.api.messages import router as message_router
from app.api.users import router as user_router
from app.api.rooms import router as room_router

# Create the main router
router = APIRouter()

# Include all sub-routers
router.include_router(chat_router)
router.include_router(message_router)
router.include_router(user_router)
router.include_router(room_router)


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    return {"status": "healthy"}


@router.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint"""
    return {"message": "Chat Service API"}
