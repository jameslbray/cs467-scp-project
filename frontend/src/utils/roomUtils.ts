/**
 * Room utilities for chat functionality
 * 
 * Provides standardized methods for room operations with a unified approach
 * regardless of room type (self-messaging, direct messaging, or group chats).
 */

/**
 * Generate a consistent room name from a list of participant IDs
 * @param participantIds Array of participant IDs
 * @returns A deterministic room name
 */
export const getRoomName = (participantIds: string[]): string => {
  // Sort the IDs to ensure consistent room names regardless of order
  const sortedIds = [...participantIds].sort();
  
  // Join with colons for the room name
  return `room:${sortedIds.join(':')}`;
};

/**
 * Get a room name for a conversation between the current user and recipients
 * @param currentUserId The current user's ID
 * @param recipientIds One or more recipient IDs
 * @returns A room name for the conversation
 */
export const getConversationRoomName = (
  currentUserId: string, 
  ...recipientIds: string[]
): string => {
  // For self-messaging, there would just be one ID
  if (recipientIds.length === 1 && recipientIds[0] === currentUserId) {
    return getRoomName([currentUserId]);
  }
  
  // For all other cases, create a room with all participants
  return getRoomName([currentUserId, ...recipientIds]);
};

/**
 * Check if a room involves a specific user
 * @param roomName The room name to check
 * @param userId The user ID to check against
 * @returns True if the room involves the user
 */
export const roomInvolvesUser = (roomName: string, userId: string): boolean => {
  if (!roomName || !roomName.startsWith('room:')) return false;
  
  // Extract all participant IDs
  const participantIds = roomName.split(':').slice(1);
  
  // Check if the user is a participant
  return participantIds.includes(userId);
};

/**
 * Check if the room is for self-messaging
 * @param roomName The room name to check
 * @returns True if it's a self-messaging room
 */
export const isSelfRoom = (roomName: string): boolean => {
  if (!roomName || !roomName.startsWith('room:')) return false;
  
  // Extract all participant IDs
  const participantIds = roomName.split(':').slice(1);
  
  // It's a self room if there's only one participant
  return participantIds.length === 1;
};

/**
 * Get all participant IDs from a room name
 * @param roomName The room name to analyze
 * @returns Array of participant IDs or empty array if invalid
 */
export const getParticipantsFromRoom = (roomName: string): string[] => {
  if (!roomName || !roomName.startsWith('room:')) return [];
  
  // Extract all participant IDs
  return roomName.split(':').slice(1);
};