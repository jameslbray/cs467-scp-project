"""
Room utilities for chat functionality

Provides standardized methods for room operations with a unified approach
regardless of room type (self-messaging, direct messaging, or group chats).
"""
from typing import List


def get_room_name(participant_ids: List[str]) -> str:
    """
    Generate a consistent room name from a list of participant IDs
    
    Args:
        participant_ids: List of participant IDs
        
    Returns:
        A deterministic room name
    """
    # Sort the IDs to ensure consistent room names regardless of order
    sorted_ids = sorted(participant_ids)
    
    # Join with colons for the room name
    return f"room:{':'.join(sorted_ids)}"


def get_conversation_room_name(current_user_id: str, *recipient_ids: str) -> str:
    """
    Get a room name for a conversation between the current user and recipients
    
    Args:
        current_user_id: The current user's ID
        recipient_ids: One or more recipient IDs
        
    Returns:
        A room name for the conversation
    """
    # For self-messaging, there would just be one ID
    if len(recipient_ids) == 1 and recipient_ids[0] == current_user_id:
        return get_room_name([current_user_id])
    
    # For all other cases, create a room with all participants
    return get_room_name([current_user_id] + list(recipient_ids))


def room_involves_user(room_name: str, user_id: str) -> bool:
    """
    Check if a room involves a specific user
    
    Args:
        room_name: The room name to check
        user_id: The user ID to check against
        
    Returns:
        True if the room involves the user
    """
    if not room_name or not room_name.startswith('room:'):
        return False
    
    # Extract all participant IDs
    participant_ids = room_name.split(':')[1:]
    
    # Check if the user is a participant
    return user_id in participant_ids


def is_self_room(room_name: str) -> bool:
    """
    Check if the room is for self-messaging
    
    Args:
        room_name: The room name to check
        
    Returns:
        True if it's a self-messaging room
    """
    if not room_name or not room_name.startswith('room:'):
        return False
    
    # Extract all participant IDs
    participant_ids = room_name.split(':')[1:]
    
    # It's a self room if there's only one participant
    return len(participant_ids) == 1


def get_participants_from_room(room_name: str) -> List[str]:
    """
    Get all participant IDs from a room name
    
    Args:
        room_name: The room name to analyze
        
    Returns:
        List of participant IDs or empty list if invalid
    """
    if not room_name or not room_name.startswith('room:'):
        return []
    
    # Extract all participant IDs
    return room_name.split(':')[1:]