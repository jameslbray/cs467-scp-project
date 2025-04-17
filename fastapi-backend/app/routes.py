from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def root():
    return {"message": "FastAPI + Socket.IO server is running!"}
