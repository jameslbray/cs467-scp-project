# fastAPI API Routers
import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from pydantic import BaseModel, Field, field_validator
from starlette.status import (
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
)

from ..core.config import get_settings
from ..core.notification_manager import NotificationManager
from ..db.models import (
    NotificationType, 
    NotificationResponse, 
    NotificationRequest,
    ErrorResponse,
    SuccessResponse
    )

# Set up OAuth2 with password flow (token-based authentication)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Create router
router = APIRouter(tags=["notifications"])

logger = logging.getLogger(__name__)
settings = get_settings()


async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """Extract and validate user ID from JWT token"""
    try:
        secret_key = settings.JWT_SECRET_KEY.get_secret_value()
        payload = jwt.decode(
            token, secret_key, algorithms=[settings.JWT_ALGORITHM]
        )
        
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        return user_id
    except jwt.JWTError:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_notification_manager():
    """Get the global NotificationManager instance from the app state"""
    from ..main import notification_manager

    if notification_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Notification service not initialized"
        )
    return notification_manager


@router.get("/notify/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Routes
@router.get(
    "/notify/{user_id}",
    response_model=list[NotificationResponse],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def get_user_notifications(
    user_id: str,
    current_user: str = Depends(get_current_user),
    notification_manager: NotificationManager = Depends(get_notification_manager),
):
    """
    Get the current notifications for a user

    Parameters:
    - **user_id**: ID of the user whose notifications are being requested

    Returns:
    - **NotificationResponse**: User's current notification information
    """
    logger.info(f"Fetching notifications for user: {user_id}")
    notification_data = await notification_manager.get_user_notifications(user_id)

    return notification_data


@router.post(
    "/notify/{user_id}",
    response_model=SuccessResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def create_user_notification(
    user_id: str,
    notification_update: NotificationRequest,
    current_user: str = Depends(get_current_user),
    notification_manager: NotificationManager = Depends(get_notification_manager),
):
    """
    Create a user notification. 
    
    Parameters:
    - **user_id**: ID of the user whose status is being updated
    - **notification_update**: New notification information

    Returns:
    - **NotificationResponse**: Created notification information
    """
    # Check if the user is trying to update their own status
    if user_id != current_user:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="You can only update your own status"
        )
    
    logger.info(f"Creating notification for user: {user_id}")

    try:
        # If user_id in the URL differs from the one in the request, ensure consistency
        if notification_update.recipient_id != user_id:
            notification_update.recipient_id = user_id
            
        response = await notification_manager.create_notification(notification_update)
        
        if not response:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail="Notification creation failed",
            )
        return {"message" : "success"}
            
    except Exception as e:
        logger.error(f"Failed to update notification: {e}")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Failed to update notification",
        )


@router.put(
    "/notify/{user_id}",
    response_model=SuccessResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def read_user_notification(
    user_id: str,
    notification_id: str = Query(..., description="ID of the notification to mark as read"),
    current_user: str = Depends(get_current_user),
    notification_manager: NotificationManager = Depends(get_notification_manager),
):
    """
    Update a user's notification status to read.

    Parameters:
    - **user_id**: ID of the user whose notification is being updated
    - **notification_id**: Notification ID to be updated

    Returns:
    - **NotificationResponse**: Updated notification information
    """
    # Check if the user is trying to update their own status
    if user_id != current_user:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="You can only update your own status"
        )
      
    logger.info(f"Updating notification {notification_id} for user: {user_id}")

    try:
        # Call the manager to mark notification as read
        success = await notification_manager.mark_notification_as_read(notification_id, user_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Notification not found or already read"
            )
            
        return "success"
        
    except Exception as e:
        logger.error(f"Failed to update notification: {e}")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Failed to update notification",
        )


@router.put(
    "/notify/all/{user_id}",
    response_model=SuccessResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def update_all_user_notifications(
    user_id: str,
    current_user: str = Depends(get_current_user),
    notification_manager: NotificationManager = Depends(get_notification_manager),
):
    """
    Update all of a user's notification status to read.

    Parameters:
    - **user_id**: ID of the user whose notification is being updated

    Returns:
    - **SuccessResponse**: Success message
    """
    # Check if the user is trying to update their own status
    if user_id != current_user:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="You can only update your own status"
        )
    
    logger.info(f"Updating all notifications for user: {user_id}")

    try:
        # Call the manager to mark notification as read
        success = await notification_manager.mark_all_notifications_as_read(user_id)
            
        return "success"
        
    except Exception as e:
        logger.error(f"Failed to update notification: {e}")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Failed to update notification",
        )

@router.delete(
    "/notify/{user_id}",
    response_model=SuccessResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def delete_read_notifications(
    user_id: str,
    current_user: str = Depends(get_current_user),
    notification_manager: NotificationManager = Depends(get_notification_manager),
):
    """
    Update a user's notifications. Post body should contain the notification_id.

    Parameters:
    - **user_id**: ID of the user whose notification is being updated
    - **notification_id**: Notification ID to be updated

    Returns:
    - **NotificationResponse**: Updated notification information
    """
    # Check if the user is trying to update their own status
    if user_id != current_user:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="You can only update your own status"
        )

    logger.info(f"Removing stale notification for user: {user_id}")

    try:
        # Call the manager to mark notification as read
        deleted_count = await notification_manager.delete_read_notifications(user_id)
            
        return f"Successfully deleted {deleted_count} notifications"
        
    except Exception as e:
        logger.error(f"Failed to update notification: {e}")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Failed to update notification",
        )


@router.get("/notify", summary="API Info")
async def api_info():
    """
    Get information about the Notification API

    Returns:
    - Basic information about the API and available endpoints
    """
    return {
        "name": "Notification Service API",
        "version": settings.VERSION,
        "description": "API for tracking and managing user notifications",
        "endpoints": {
            "GET /notify/health": "Health check endpoint",
            "GET /notify/health": "Health check endpoint",
            "GET /api/notify/{user_id}": "Get a user's current notifications",
            "POST /api/notify/{user_id}": "Create a notification for a user",
            "PUT /api/notify/{user_id}": "Mark a notification as read",
            "PUT /api/notify/all/{user_id}": "Mark all notifications as read",
            "DELETE /api/notify/{user_id}": "Delete read notifications",
            
        },
    }
