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

from services.connections.app.core.config import get_settings
from services.connections.app.core.connection_manager import ConnectionManager
from services.connections.app.db.schemas import (
    ConnectionSchema,
    ConnectionCreate,
    ErrorResponse,
)

# Set up OAuth2 with password flow (token-based authentication)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Create router
router = APIRouter(tags=["connections"])

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


# Routes
@router.get(
    "/connect/{user_id}",
    response_model=list[ConnectionSchema],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def get_user_connections(
    user_id: str,
    # current_user: str = Depends(get_current_user),
    connection_manager: ConnectionManager = Depends(get_connection_manager),
):
    """
    Get the connections for a user

    Parameters:
    - **user_id**: ID of the user whose connections are being requested

    Returns:
    - **ConnectionResponse**: User's current connection information
    """
    # if current_user != user_id:
    #     raise HTTPException(
    #         status_code=HTTP_403_FORBIDDEN,
    #         detail="You can only view your own connections",
    #     )

    logger.info(f"Fetching connections for user: {user_id}")
    connection_data = await connection_manager.get_user_connections()

    return connection_data


@router.get(
    "/connect/all",
    response_model=list[ConnectionSchema]
)
async def get_all_connections(
    connection_manager: ConnectionManager = Depends(get_connection_manager),
):
    """
    Get all connections in the database

    Returns:
    - **list[Connection]**: All user connections
    """
    logger.info("Fetching all user connections")
    connection_data = await connection_manager.get_all_connections()

    return connection_data


@router.post(
    "/connect/",
    response_model=ConnectionSchema,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def create_connection(
    connection_data: ConnectionCreate,
    # current_user: str = Depends(get_current_user),
    connection_manager: ConnectionManager = Depends(get_connection_manager),
):
    """
    Create a connection between user_id and friend_id.

    Parameters:
    - **user_id**: ID of the user whose sending the request
    - **friend_id**: ID of the friend to connect with

    Returns:
    - **Connection**: Created Connection information
    """
    # Check if the user is trying to update their own status
    # if connection_data.user_id != current_user:
    #     raise HTTPException(
    #         status_code=HTTP_403_FORBIDDEN,
    #         detail="You can only update your own status"
    #     )

    logger.info(f"Creating connection for user: {connection_data.user_id}")

    try:
        response = await connection_manager.create_connection(connection_data)

        if not response:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail="Connection creation failed",
            )
        return response

    except Exception as e:
        logger.error(f"Failed to update connection: {e}")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Failed to update connection",
        )


# @router.put(
#     "/notify/{user_id}",
#     response_model=SuccessResponse,
#     responses={
#         400: {"model": ErrorResponse, "description": "Bad request"},
#         401: {"model": ErrorResponse, "description": "Unauthorized"},
#         403: {"model": ErrorResponse, "description": "Forbidden"},
#         404: {"model": ErrorResponse, "description": "User not found"},
#     },
# )
# async def create_user_notification(
#     user_id: str,
#     notification_id: str = Query(..., description="ID of the notification to mark as read"),
#     # current_user: str = Depends(get_current_user),
#     notification_manager: NotificationManager = Depends(get_notification_manager),
# ):
#     """
#     Update a user's notification status to read.

#     Parameters:
#     - **user_id**: ID of the user whose notification is being updated
#     - **notification_id**: Notification ID to be updated

#     Returns:
#     - **NotificationResponse**: Updated notification information
#     """
#     # Check if the user is trying to update their own status
#     # if user_id != current_user:
#     #     raise HTTPException(
#     #         status_code=HTTP_403_FORBIDDEN,
#     #         detail="You can only update your own status"
#     #     )


#     logger.info(f"Updating notification {notification_id} for user: {user_id}")

#     try:
#         # Call the manager to mark notification as read
#         success = await notification_manager.mark_notification_as_read(notification_id, user_id)

#         if not success:
#             raise HTTPException(
#                 status_code=404,
#                 detail="Notification not found or already read"
#             )

#         return SuccessResponse(message="success")

#     except Exception as e:
#         logger.error(f"Failed to update notification: {e}")
#         raise HTTPException(
#             status_code=HTTP_404_NOT_FOUND,
#             detail="Failed to update notification",
#         )


# @router.put(
#     "/notify/all/{user_id}",
#     response_model=SuccessResponse,
#     responses={
#         400: {"model": ErrorResponse, "description": "Bad request"},
#         401: {"model": ErrorResponse, "description": "Unauthorized"},
#         403: {"model": ErrorResponse, "description": "Forbidden"},
#         404: {"model": ErrorResponse, "description": "User not found"},
#     },
# )
# async def update_all_user_notifications(
#     user_id: str,
#     # current_user: str = Depends(get_current_user),
#     notification_manager: NotificationManager = Depends(get_notification_manager),
# ):
#     """
#     Update all of a user's notification status to read.

#     Parameters:
#     - **user_id**: ID of the user whose notification is being updated

#     Returns:
#     - **SuccessResponse**: Success message
#     """
#     # Check if the user is trying to update their own status
#     # if user_id != current_user:
#     #     raise HTTPException(
#     #         status_code=HTTP_403_FORBIDDEN,
#     #         detail="You can only update your own status"
#     #     )


#     logger.info(f"Updating all notifications for user: {user_id}")

#     try:
#         # Call the manager to mark notification as read
#         success = await notification_manager.mark_all_notifications_as_read(user_id)

#         return SuccessResponse(message="success")

#     except Exception as e:
#         logger.error(f"Failed to update notification: {e}")
#         raise HTTPException(
#             status_code=HTTP_404_NOT_FOUND,
#             detail="Failed to update notification",
#         )

# @router.delete(
#     "/notify/{user_id}",
#     response_model=SuccessResponse,
#     responses={
#         400: {"model": ErrorResponse, "description": "Bad request"},
#         401: {"model": ErrorResponse, "description": "Unauthorized"},
#         403: {"model": ErrorResponse, "description": "Forbidden"},
#         404: {"model": ErrorResponse, "description": "User not found"},
#     },
# )
# async def delete_read_notifications(
#     user_id: str,
#     # current_user: str = Depends(get_current_user),
#     notification_manager: NotificationManager = Depends(get_notification_manager),
# ):
#     """
#     Update a user's notifications. Post body should contain the notification_id.

#     Parameters:
#     - **user_id**: ID of the user whose notification is being updated
#     - **notification_id**: Notification ID to be updated

#     Returns:
#     - **NotificationResponse**: Updated notification information
#     """
#     # Check if the user is trying to update their own status
#     # if user_id != current_user:
#     #     raise HTTPException(
#     #         status_code=HTTP_403_FORBIDDEN,
#     #         detail="You can only update your own status"
#     #     )


#     logger.info(f"Removing stale notification for user: {user_id}")

#     try:
#         # Call the manager to mark notification as read
#         deleted_count = await notification_manager.delete_read_notifications(user_id)

#         return SuccessResponse(message="Successfully deleted {deleted_count} notifications")

#     except Exception as e:
#         logger.error(f"Failed to update notification: {e}")
#         raise HTTPException(
#             status_code=HTTP_404_NOT_FOUND,
#             detail="Failed to update notification",
#         )


# # @router.get(
# #     "/notify/friends/{user_id}",
# #     response_model=FriendStatusesResponse,
# #     responses={
# #         401: {"model": ErrorResponse, "description": "Unauthorized"},
# #         403: {"model": ErrorResponse, "description": "Forbidden"},
# #         404: {"model": ErrorResponse, "description": "User not found"},
# #     },
# # )
# # async def get_friend_statuses(
# #     user_id: str,
# #     current_user: str = Depends(get_current_user),
# #     presence_manager: PresenceManager = Depends(get_presence_manager),
# # ):
# #     """
# #     Get the status of all friends of a user

# #     Parameters:
# #     - **user_id**: ID of the user whose friends' statuses are being requested

# #     Returns:
# #     - **FriendStatusesResponse**: Status information for all friends
# #     """
# #     # Check if the user is requesting their own friends' statuses
# #     if user_id != current_user:
# #         raise HTTPException(
# #             status_code=HTTP_403_FORBIDDEN,
# #             detail="You can only view your own friends' statuses",
# #         )

# #     # Get friend IDs
# #     friend_ids = await presence_manager._get_friend_ids(user_id)

# #     # Get status for each friend
# #     statuses = {}
# #     for friend_id in friend_ids:
# #         status_data = await presence_manager.get_user_status(friend_id)
# #         statuses[friend_id] = StatusResponse(
# #             user_id=friend_id,
# #             status=status_data.get("status", "offline"),
# #             last_seen=status_data.get("last_seen"),
# #         )

# #     return FriendStatusesResponse(statuses=statuses)


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
        },
    }
