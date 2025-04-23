from fastapi import APIRouter, HTTPException, Depends
from app.schemas.user import UserCreate, UserResponse, UserListResponse
from app.core.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])

# Dependency to get user service


async def get_user_service():
    # This would be properly injected in a real application
    # For now, we'll just return a placeholder
    return UserService()


@router.get("/", response_model=UserListResponse)
async def get_users(user_service: UserService = Depends(get_user_service)):
    """Get all users"""
    try:
        users = await user_service.get_users()
        return {"users": users}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=UserResponse)
async def create_user(
    user: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    """Create a new user"""
    try:
        new_user = await user_service.create_user(user)
        return new_user
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    user_service: UserService = Depends(get_user_service)
):
    """Get a specific user by ID"""
    try:
        user = await user_service.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
