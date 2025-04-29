from fastapi import APIRouter, HTTPException, Depends
from app.schemas.room import RoomCreate, RoomResponse, RoomListResponse
from app.core.room_service import RoomService

router = APIRouter(prefix="/rooms", tags=["rooms"])

# Dependency to get room service


async def get_room_service():
    # This would be properly injected in a real application
    # For now, we'll just return a placeholder
    return RoomService()


@router.get("/", response_model=RoomListResponse)
async def get_rooms(room_service: RoomService = Depends(get_room_service)):
    """Get all rooms"""
    try:
        rooms = await room_service.get_rooms()
        return {"rooms": rooms}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=RoomResponse)
async def create_room(
    room: RoomCreate, room_service: RoomService = Depends(get_room_service)
):
    """Create a new room"""
    try:
        new_room = await room_service.create_room(room)
        return new_room
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{room_id}", response_model=RoomResponse)
async def get_room(room_id: str, room_service: RoomService = Depends(get_room_service)):
    """Get a specific room by ID"""
    try:
        room = await room_service.get_room(room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        return room
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
