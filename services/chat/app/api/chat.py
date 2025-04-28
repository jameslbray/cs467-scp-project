from fastapi import APIRouter, HTTPException, Depends
from app.schemas.chat import ChatCreate, ChatResponse, ChatListResponse
from app.core.chat_service import ChatService
router = APIRouter(prefix="/chats", tags=["chats"])

# TODO: Redo with new folder structure
async def get_chat_service():
    # This would be properly injected in a real application
    # For now, we'll just return a placeholder
    return ChatService()


@router.get("/", response_model=ChatListResponse)
async def get_chats(chat_service: ChatService = Depends(get_chat_service)):
    """Get all chats for the current user"""
    try:
        chats = await chat_service.get_user_chats()
        return {"chats": chats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=ChatResponse)
async def create_chat(
    chat: ChatCreate, chat_service: ChatService = Depends(get_chat_service)
):
    """Create a new chat"""
    try:
        new_chat = await chat_service.create_chat(chat)
        return new_chat
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat(
        chat_id: str, chat_service: ChatService = Depends(get_chat_service)):
    """Get a specific chat by ID"""
    try:
        chat = await chat_service.get_chat(chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        return chat
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
