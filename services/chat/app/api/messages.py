from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.schemas.message import MessageCreate, MessageResponse, MessageListResponse
from app.core.message_service import MessageService

router = APIRouter(prefix="/messages", tags=["messages"])

# Dependency to get message service


async def get_message_service():
    # This would be properly injected in a real application
    # For now, we'll just return a placeholder
    return MessageService()


@router.get("/chat/{chat_id}", response_model=MessageListResponse)
async def get_chat_messages(
    chat_id: str,
    message_service: MessageService = Depends(get_message_service)
):
    """Get all messages for a specific chat"""
    try:
        messages = await message_service.get_chat_messages(chat_id)
        return {"messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=MessageResponse)
async def create_message(
    message: MessageCreate,
    message_service: MessageService = Depends(get_message_service)
):
    """Create a new message"""
    try:
        new_message = await message_service.create_message(message)
        return new_message
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: str,
    message_service: MessageService = Depends(get_message_service)
):
    """Get a specific message by ID"""
    try:
        message = await message_service.get_message(message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        return message
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
