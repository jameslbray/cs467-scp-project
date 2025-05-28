# fastAPI API Routers
import logging
from datetime import datetime
from typing import Dict, List, Optional
import httpx
import asyncio

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
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from services.connections.app.core.config import get_settings
from services.connections.app.core.connection_manager import ConnectionManager
from services.connections.app.db.schemas import (
    Connection,
    ErrorResponse,
    ConnectionCreate,
    ConnectionUpdate
    )

# Set up OAuth2 with password flow (token-based authentication)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Create router
router = APIRouter(tags=["connections"])

logger = logging.getLogger(__name__)
settings = get_settings()

class UserInfo(BaseModel):
    """Model for user information"""
    id: str
    username: str
    profile_picture_url: Optional[str] = None

async def get_user_from_api(user_id: str, token: str) -> UserInfo:
    """Get user info from the users service"""
    users_service_url = "http://localhost:8001"  # Can be moved to config settings
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{users_service_url}/api/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to get user info: {response.text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to get user info: {response.text}"
            )
            
        return UserInfo.parse_obj(response.json())

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
                status_code=HTTP_401_UNAUTHORIZED,
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

def get_connection_manager():
    """Get the global ConnectionManager instance from the app state"""
    from ..main import connection_manager

    if connection_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Connection service not initialized"
        )
    return connection_manager


@router.get(
    "/connect/health",
    response_model=Dict[str, str])
async def health_check(
    connection_manager: ConnectionManager = Depends(get_connection_manager)
):
    """Health check endpoint."""
    return {"status": "healthy"} if await connection_manager.check_connection_health() else {"status": "unhealthy"}


@router.get(
    "/connect/all",
    response_model=list[Connection]
)
async def get_all_connections(
    connection_manager: ConnectionManager = Depends(get_connection_manager),
):
    """
    Get all connections in the database. Useful for admin purposes or debugging.

    Returns:
    - **list[Connection]**: All user connections
    """
    logger.info(f"Fetching all user connections")
    connection_data = await connection_manager.get_all_connections()

    return connection_data


# Routes
@router.get(
    "/connect/{user_id}",
    response_model=list[Connection],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def get_user_connections(
    user_id: str,
    current_user: str = Depends(get_current_user),
    connection_manager: ConnectionManager = Depends(get_connection_manager),
):
    """
    Get the connections for a user

    Parameters:
    - **user_id**: ID of the user whose connections are being requested

    Returns:
    - **ConnectionResponse**: User's current connection information
    """
    if str(current_user) != str(user_id):
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="You can only view your own connections",
        )

    logger.info(f"Fetching connections for user: {user_id}")
    connection_data = await connection_manager.get_user_connections(user_id)

    return connection_data


@router.post(
    "/connect",
    response_model=Connection,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def create_connection(
    connection_data: ConnectionCreate,
    current_user: str = Depends(get_current_user),
    connection_manager: ConnectionManager = Depends(get_connection_manager),
    token: str = Depends(oauth2_scheme),  # Get the token for authorization
):
    """
    Create a connection between user_id and friend_id.

    Parameters:
    - **user_id**: ID of the user whose sending the request
    - **friend_id**: ID of the friend to connect with

    Returns:
    - **Connection**: Created Connection information
    """
    # Check if user_id matches the authenticated user
    if str(connection_data.user_id) != str(current_user):
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="You can only create connections for yourself"
        )

    logger.info(f"Creating connection from {connection_data.user_id} to {connection_data.friend_id}")
    
    # If this is a friend request (pending status), publish notification event
    if getattr(connection_data, "status", None) == "pending":
        try:
            # Create connection
            connection = await connection_manager.create_connection(
                connection_data
            )

            # Only proceed if connection was created successfully
            if connection is not None:
                # Define sender and recipient IDs
                sender_id = str(connection_data.user_id)
                recipient_id = str(connection_data.friend_id)

                # Publish notification with retry logic
                notification_success = False
                for attempt in range(3):  # Try 3 times
                    notification_success = await connection_manager.publish_notification_event(
                        reference_id=connection.id,
                        sender_id=sender_id,
                        recipient_id=recipient_id,
                        notification_type="friend_request",
                        content_preview="You have a new friend request"
                    )
                    if notification_success:
                        break
                    await asyncio.sleep(1)  # Wait before retrying

                if not notification_success:
                    logger.warning(
                        "Could not publish notification after multiple attempts, "
                        "but connection was created"
                    )

            return connection
        except Exception as e:
            logger.error(f"Failed to create connection: {e}")
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create connection"
            )


@router.put(
    "/connect",
    response_model=Connection,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def update_connection(
    connection_data: ConnectionUpdate,
    current_user: str = Depends(get_current_user),
    connection_manager: ConnectionManager = Depends(get_connection_manager),
    token: str = Depends(oauth2_scheme),
):
    """
    Update a user's connection status.

    Parameters:
    - **connection_data**: ConnectionUpdate object containing user_id, friend_id, and status

    Returns:
    - **Connection**: Updated connection information
    """
    # Check if the user is trying to update their own connection
    if str(connection_data.user_id) != str(current_user):
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="You can only update your own connections"
        )

    logger.info(f"Updating connection {connection_data.user_id} -> {connection_data.status} -> {connection_data.friend_id}")

    try:
        # Call the manager to update connection status
        original_connection = await connection_manager.get_connection(connection_data.user_id, connection_data.friend_id)
        response = await connection_manager.update_connection(connection_data)

        if not response:
            raise HTTPException(
                status_code=404,
                detail="Connection not found"
            )
            
        # If this was accepting a friend request, send notification to the other user
        if original_connection and original_connection.status == "pending" and connection_data.status == "accepted":
            try:
                # Get user information
                accepter_info = await get_user_from_api(connection_data.user_id, token)
                accepter_name = accepter_info.username
                
                # Determine who is the original sender (to notify them)
                original_sender_id = str(original_connection.user_id)
                if original_sender_id == str(connection_data.user_id):
                    # If the current user was the original sender, notify the friend
                    recipient_id = str(connection_data.friend_id)
                else:
                    # Otherwise notify the original sender
                    recipient_id = original_sender_id
                
                # Publish friend acceptance event
                await connection_manager.publish_notification_event(
                    recipient_id=recipient_id,
                    sender_id=str(connection_data.user_id),
                    reference_id=str(response.id),
                    notification_type="friend_accepted",
                    content_preview=f"{accepter_name} accepted your friend request"
                )
                
                logger.info(f"Published friend acceptance notification to {recipient_id}")
            except Exception as e:
                # Log error but don't fail request
                logger.error(f"Failed to publish friend acceptance notification: {e}")

        return response

    except Exception as e:
        logger.error(f"Failed to update connection: {e}")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Failed to update connection",
        )

# Uncomment the following code if you want to implement WebSocket subscriptions for status updates
# @router.websocket("/ws/status/subscribe")
# async def status_updates_websocket(
#     websocket: WebSocket,
#     token: str = Query(...),
#     presence_manager: PresenceManager = Depends(get_presence_manager),
# ):
#     """
#     WebSocket endpoint to subscribe to status updates for multiple users

#     Connect with a valid JWT token and send a JSON message with user_ids to
#     subscribe to
#     """
#     # Authenticate the user
#     try:
#         payload = jwt.decode(
#             token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
#         )
#         user_id = payload.get("sub")
#         if user_id is None:
#             await websocket.close(code=1008)  # Policy violation
#             return
#     except jwt.PyJWTError:
#         await websocket.close(code=1008)  # Policy violation
#         return

#     await websocket.accept()

#     try:
#         # Wait for the subscription request
#         data = await websocket.receive_json()
#         user_ids = data.get("user_ids", [])

#         if not user_ids:
#             await websocket.send_json({
#                 "type": "error",
#                 "message": "No user IDs provided for subscription"
#             })
#             return

#         # Send initial status for all requested users
#         initial_statuses = {}
#         for subscription_user_id in user_ids:
#             status_data = await presence_manager.get_user_status(subscription_user_id)
#             initial_statuses[subscription_user_id] = {
#                 "status": status_data.get("status", "offline"),
#                 "last_seen": status_data.get("last_seen"),
#             }

#         await websocket.send_json(
#             {"type": "initial_statuses", "statuses": initial_statuses}
#         )

#         # TODO: Set up subscriptions in the presence manager
#         # This would typically involve registering the websocket as a listener
#         # for status updates from the specified users

#         # For now, we'll simply confirm the subscription
#         await websocket.send_json(
#             {"type": "subscription_confirmed", "subscribed_to": user_ids}
#         )

#         # Keep the connection open and handle updates
#         while True:
#             # Wait for any client messages
#             data = await websocket.receive_text()

#             # If we receive a ping, send a pong
#             if data == "ping":
#                 await websocket.send_text("pong")

#     except WebSocketDisconnect:
#         logger.info(f"WebSocket client disconnected: {user_id}")
#         # TODO: Clean up subscriptions
#     except Exception as e:
#         logger.error(f"Error in status updates websocket: {e}")
#         await websocket.close(code=1011)  # Internal error


# @router.post(
#     "/notify/subscribe",
#     response_model=SubscriptionResponse,
#     responses={
#         401: {"model": ErrorResponse, "description": "Unauthorized"},
#         400: {"model": ErrorResponse, "description": "Bad request"},
#     },
# )
# async def subscribe_to_status_updates(
#     subscription: SubscriptionRequest,
#     current_user: str = Depends(get_current_user),
#     presence_manager: PresenceManager = Depends(get_presence_manager),
# ):
#     """
#     Subscribe to status updates for multiple users (HTTP fallback)

#     This is a placeholder for services that can't use WebSockets.
#     You would typically poll /status/friends/{user_id} to get updates.

#     Parameters:
#     - **subscription**: Subscription request with user IDs to monitor

#     Returns:
#     - **SubscriptionResponse**: Confirmation of subscription
#     """
#     # This is a placeholder for services that can't use WebSockets
#     # In a real implementation, this would set up a subscription and
#     # clients would poll for updates

#     if len(subscription.user_ids) > 0:
#         return SubscriptionResponse(
#             success=True, subscribed_users=subscription.user_ids
#         )
#     else:
#         return SubscriptionResponse(
#             success=False, subscribed_users=[], message="No user IDs provided"
#         )


@router.get("/connect", summary="API Info")
async def api_info():
    """
    Get information about the Connections API

    Returns:
    - Basic information about the API and available endpoints
    """
    return {
        "name": "Connections Service API",
        "version": settings.VERSION,
        "description": "API for managing user connections",
        "endpoints": {
            "GET /connect/health": "Health check endpoint",
            "GET /connect/{user_id}": "Get a user's connections",
            "GET /connect/all": "Get all connections",
            "POST /connect": "Create a new connection",
            "PUT /connect": "Update a connection",
        },
    }
