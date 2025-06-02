import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import type { ChatMessageType } from '../types/chatMessageType';

interface NotificationContextType {
  showNotification: (message: ChatMessageType, roomName: string) => void;
  activeRoomId: string | null;
  setActiveRoomId: (roomId: string | null) => void;
}

const NotificationContext = createContext<NotificationContextType | null>(null);

export const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
};

export const NotificationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeRoomId, setActiveRoomId] = useState<string | null>(null);
  const lastNotificationTime = useRef<Record<string, number>>({});
  
  // Request notification permission on mount
  useEffect(() => {
    if ('Notification' in window) {
      Notification.requestPermission();
    }
  }, []);

  const showNotification = (message: ChatMessageType, roomName: string) => {
    // Don't show notification if user is viewing this room
    if (activeRoomId === message.room_id) return;
    
    // Throttle notifications - only one per 3 minutes per room
    const now = Date.now();
    const lastTime = lastNotificationTime.current[message.room_id] || 0;
    
    if (now - lastTime < 3 * 60 * 1000) {
      // Less than 3 minutes since last notification for this room
      return;
    }
    
    // Update last notification time for this room
    lastNotificationTime.current[message.room_id] = now;

    // Create notification
    if ('Notification' in window && Notification.permission === 'granted') {
      const senderName = 'Someone';
      const notificationContent = new Notification(`New message in ${roomName}`, {
        body: `${senderName}: ${message.content.substring(0, 50)}${message.content.length > 50 ? '...' : ''}`,
        icon: '/logo.png'
      });
      
      // When notification is clicked, focus window and navigate to that room
      notificationContent.onclick = () => {
        window.focus();
        // Implement room navigation here if needed
      };
    }
  };

  return (
    <NotificationContext.Provider value={{ showNotification, activeRoomId, setActiveRoomId }}>
      {children}
    </NotificationContext.Provider>
  );
};