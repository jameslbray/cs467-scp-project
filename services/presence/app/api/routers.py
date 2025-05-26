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

from ..core.config import settings
from ..core.presence_manager import PresenceManager

# Set up OAuth2 with password flow (token-based authentication)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Create router
router = APIRouter(tags=["presence"])

logger = logging.getLogger(__name__)

# Define models for requests and responses


class StatusUpdate(BaseModel):
    """Model for status update requests"""

    status: str
    additional_info: Optional[str] = None

    @field_validator("status")
    def status_must_be_valid(cls, v):
        valid_statuses = ["online", "offline", "away", "busy", "invisible"]
        if v not in valid_statuses:
            raise ValueError(
                f"Status must be one of: {', '.join(valid_statuses)}"
            )
        return v


class StatusResponse(BaseModel):
    """Model for status responses"""

    user_id: str
    status: str
    last_seen: Optional[float] = None
    additional_info: Optional[str] = None


class FriendStatusesResponse(BaseModel):
    """Model for friend statuses response"""

    statuses: Dict[str, StatusResponse]
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class SubscriptionRequest(BaseModel):
    """Model for status subscription requests"""

    user_ids: List[str] = Field(
        default=...,
        min_items=1,
        max_items=100
    )


class SubscriptionResponse(BaseModel):
    """Model for status subscription responses"""

    success: bool
    subscribed_users: List[str]
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    """Model for error responses"""

    detail: str
    status_code: int
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# Dependency to get the current user from JWT token
async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """Extract and validate user ID from JWT token"""
    try:
        secret_key = settings.JWT_SECRET_KEY.get_secret_value()
        payload = jwt.decode(
            token, secret_key, algorithms=[settings.JWT_ALGORITHM]
        )

        # Try both 'sub' and 'username' claims
        username: str = payload.get("sub") or payload.get("username")
        if username is None:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return username
    except jwt.JWTError:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Dependency to get the PresenceManager instance


def get_presence_manager():
    """Get the global PresenceManager instance from the app state"""
    from ..main import presence_manager

    if presence_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Presence service not initialized"
        )
    return presence_manager


# Routes
@router.get("/presence/health")
async def health_check(
        presence_manager: PresenceManager = Depends(get_presence_manager),
):
    """Health check endpoint."""
    return {"status": "healthy"} if await presence_manager.check_connection_health() else {"status": "unhealthy"}

@router.get(
    "/status/{user_id}",
    response_model=StatusResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def get_user_status(
    user_id: str,
    current_user: str = Depends(get_current_user),
    presence_manager: PresenceManager = Depends(get_presence_manager),
):
    """
    Get the current status of a user

    Parameters:
    - **user_id**: ID of the user whose status is being requested

    Returns:
    - **StatusResponse**: User's current status information
    """
    status_data = await presence_manager.get_user_status(user_id)

    # Create response with required fields
    return StatusResponse(
        user_id=user_id,
        status=status_data.get("status", "offline"),
        last_seen=status_data.get("last_seen"),
    )


@router.put(
    "/status/{user_id}",
    response_model=StatusResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def update_user_status(
    user_id: str,
    status_update: StatusUpdate,
    current_user: str = Depends(get_current_user),
    presence_manager: PresenceManager = Depends(get_presence_manager),
):
    """
    Update a user's status (users can only update their own status)

    Parameters:
    - **user_id**: ID of the user whose status is being updated
    - **status_update**: New status information

    Returns:
    - **StatusResponse**: Updated status information
    """
    # Check if the user is trying to update their own status
    if user_id != current_user:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="You can only update your own status"
        )

    # Update status
    success = await presence_manager.set_user_status(
        user_id,
        status_update.status
    )
    if not success:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="User not found or status update failed",
        )

    # Get updated status
    status_data = await presence_manager.get_user_status(user_id)

    # Create response
    return StatusResponse(
        user_id=user_id,
        status=status_data.get("status", "offline"),
        last_seen=status_data.get("last_seen"),
        additional_info=status_update.additional_info,
    )


@router.post(
    "/status/register/{user_id}",
    response_model=StatusResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"}
    },
)
async def register_user_status(
    user_id: str,
    current_user: str = Depends(get_current_user),
    presence_manager: PresenceManager = Depends(get_presence_manager),
):
    """
    Register a new user's status

    Parameters:
    - **user_id**: ID of the user whose status is being updated

    Returns:
    - **StatusResponse**: New status information
    """
    if user_id != current_user:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="You can only register your own status"
        )

    # Update status
    success = await presence_manager.set_new_user_status(
        user_id
    )
    if not success:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="User not found or status update failed",
        )

    # Get updated status
    status_data = await presence_manager.get_user_status(user_id)

    # Create response
    return StatusResponse(
        user_id=user_id,
        status=status_data.get("status", "offline"),
        last_seen=status_data.get("last_seen")
    )

@router.get(
    "/status/friends/{user_id}",
    response_model=FriendStatusesResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def get_friend_statuses(
    user_id: str,
    current_user: str = Depends(get_current_user),
    presence_manager: PresenceManager = Depends(get_presence_manager),
):
    """
    Get the status of all friends of a user

    Parameters:
    - **user_id**: ID of the user whose friends' statuses are being requested

    Returns:
    - **FriendStatusesResponse**: Status information for all friends
    """
    # Check if the user is requesting their own friends' statuses
    if user_id != current_user:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="You can only view your own friends' statuses",
        )

    # Get friend IDs
    friend_ids = await presence_manager._get_friend_ids(user_id)

    # Get status for each friend
    statuses = {}
    for friend_id in friend_ids:
        status_data = await presence_manager.get_user_status(friend_id)
        statuses[friend_id] = StatusResponse(
            user_id=friend_id,
            status=status_data.get("status", "offline"),
            last_seen=status_data.get("last_seen"),
        )

    return FriendStatusesResponse(statuses=statuses)


@router.websocket("/ws/status/subscribe")
async def status_updates_websocket(
    websocket: WebSocket,
    token: str = Query(...),
    presence_manager: PresenceManager = Depends(get_presence_manager),
):
    """
    WebSocket endpoint to subscribe to status updates for multiple users

    Connect with a valid JWT token and send a JSON message with user_ids to
    subscribe to
    """
    # Authenticate the user
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = payload.get("sub")
        if user_id is None:
            await websocket.close(code=1008)  # Policy violation
            return
    except jwt.PyJWTError:
        await websocket.close(code=1008)  # Policy violation
        return

    await websocket.accept()

    try:
        # Wait for the subscription request
        data = await websocket.receive_json()
        user_ids = data.get("user_ids", [])

        if not user_ids:
            await websocket.send_json({
                "type": "error",
                "message": "No user IDs provided for subscription"
            })
            return

        # Send initial status for all requested users
        initial_statuses = {}
        for subscription_user_id in user_ids:
            status_data = await presence_manager.get_user_status(subscription_user_id)
            initial_statuses[subscription_user_id] = {
                "status": status_data.get("status", "offline"),
                "last_seen": status_data.get("last_seen"),
            }

        await websocket.send_json(
            {"type": "initial_statuses", "statuses": initial_statuses}
        )

        # TODO: Set up subscriptions in the presence manager
        # This would typically involve registering the websocket as a listener
        # for status updates from the specified users

        # For now, we'll simply confirm the subscription
        await websocket.send_json(
            {"type": "subscription_confirmed", "subscribed_to": user_ids}
        )

        # Keep the connection open and handle updates
        while True:
            # Wait for any client messages
            data = await websocket.receive_text()

            # If we receive a ping, send a pong
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {user_id}")
        # TODO: Clean up subscriptions
    except Exception as e:
        logger.error(f"Error in status updates websocket: {e}")
        await websocket.close(code=1011)  # Internal error


@router.post(
    "/status/subscribe",
    response_model=SubscriptionResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        400: {"model": ErrorResponse, "description": "Bad request"},
    },
)
async def subscribe_to_status_updates(
    subscription: SubscriptionRequest,
    current_user: str = Depends(get_current_user),
    presence_manager: PresenceManager = Depends(get_presence_manager),
):
    """
    Subscribe to status updates for multiple users (HTTP fallback)

    This is a placeholder for services that can't use WebSockets.
    You would typically poll /status/friends/{user_id} to get updates.

    Parameters:
    - **subscription**: Subscription request with user IDs to monitor

    Returns:
    - **SubscriptionResponse**: Confirmation of subscription
    """
    # This is a placeholder for services that can't use WebSockets
    # In a real implementation, this would set up a subscription and
    # clients would poll for updates

    if len(subscription.user_ids) > 0:
        return SubscriptionResponse(
            success=True, subscribed_users=subscription.user_ids
        )
    else:
        return SubscriptionResponse(
            success=False, subscribed_users=[], message="No user IDs provided"
        )


@router.get("/", summary="API Info")
async def api_info():
    """
    Get information about the Presence API

    Returns:
    - Basic information about the API and available endpoints
    """
    return {
        "name": "Presence Service API",
        "version": settings.VERSION,
        "description": "API for tracking and managing user presence status",
        "endpoints": {
            "GET /api/status/{user_id}": "Get a user's current status",
            "PUT /api/status/{user_id}": "Update a user's status",
            "GET /api/status/friends/{user_id}": "Get status of all friends",
            "WS /api/ws/status/subscribe": "WebSocket for real-time status updates",
            "POST /api/status/subscribe": "HTTP fallback for status subscriptions",
        },
    }
