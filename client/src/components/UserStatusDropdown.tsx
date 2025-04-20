import React, { useState, useEffect } from 'react';
import { io, Socket } from 'socket.io-client';
import { ClientEvents, ServerEvents } from '../types';

// Define types based on server/presence/models.py
type StatusType = 'online' | 'away' | 'offline' | '';

interface UserStatus {
  userId: string;
  status: StatusType;
  last_changed: string;
}

// Style types
type StyleObject = Record<string, React.CSSProperties>;

const UserStatusDropdown: React.FC = () => {
  const [status, setStatus] = useState<StatusType>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<string>('');
  const [socket, setSocket] = useState<Socket | null>(null);
  const userId = '1'; // This should be the actual user ID from your auth system
  
  // Connect to socket server when component mounts
  useEffect(() => {
    // Initialize socket connection
    const socketConnection = io('http://localhost:3001'); // Your server.py port
    setSocket(socketConnection);
    
    // Set up event listeners
    socketConnection.on('connect', () => {
      console.log('Connected to socket server');
      
      // Request current status after connection
      socketConnection.emit(ClientEvents.REQUEST_FRIEND_STATUSES, {});
    });
    
    // Listen for status update confirmations
    socketConnection.on(ServerEvents.STATUS_UPDATED, (data: UserStatus) => {
      setStatus(data.status);
      setMessage(`Status updated to ${data.status}`);
      setIsLoading(false);
    });
    
    // Listen for friend status changes (including our own)
    socketConnection.on(ServerEvents.FRIEND_STATUS_CHANGED, (data: UserStatus) => {
      if (data.user_id === userId) {
        setStatus(data.status);
      }
    });
    
    // Listen for all friend statuses
    socketConnection.on(ServerEvents.FRIEND_STATUSES, (data: { statuses: Record<string, UserStatus> }) => {
      const myStatus = data.statuses[userId];
      if (myStatus) {
        setStatus(myStatus.status);
      }
    });
    
    // Listen for errors
    socketConnection.on(ServerEvents.ERROR, (data: { message: string }) => {
      setMessage(`Error: ${data.message}`);
      setIsLoading(false);
    });
    
    // Clean up on unmount
    return () => {
      socketConnection.disconnect();
    };
  }, [userId]);
  
  const handleStatusChange = (e: React.ChangeEvent<HTMLSelectElement>): void => {
    const newStatus = e.target.value as StatusType;
    setStatus(newStatus);
    setIsLoading(true);
    setMessage('');
    
    if (socket && socket.connected) {
      // Use socket to update status based on your presence/events.py
      socket.emit(ClientEvents.UPDATE_STATUS, {
        status: newStatus
      });
    } else {
      // Fallback if socket is not connected
      setIsLoading(false);
      setMessage('Error: Not connected to server');
    }
  };
  
  return (
    <div className="status-dropdown-container" style={styles.container}>
      <h2>User Status Updater (User ID: {userId})</h2>
      <div style={styles.connectionIndicator}>
        {socket?.connected ? 
          <span style={styles.connected}>Connected to socket server</span> : 
          <span style={styles.disconnected}>Not connected to socket server</span>
        }
      </div>
      
      <div style={styles.dropdownContainer}>
        <label htmlFor="status-select" style={styles.label}>
          Status:
        </label>
        <select
          id="status-select"
          value={status}
          onChange={handleStatusChange}
          disabled={isLoading}
          style={styles.select}
        >
          <option value="" disabled>Select status...</option>
          <option value="online">Online</option>
          <option value="away">Away</option>
          <option value="offline">Offline</option>
        </select>
        
        {isLoading && <span style={styles.loading}>Updating...</span>}
      </div>
      
      {message && (
        <div style={
          message.includes('Error') 
            ? {...styles.message, ...styles.errorMessage}
            : {...styles.message, ...styles.successMessage}
        }>
          {message}
        </div>
      )}
      
      <div style={styles.statusIndicator}>
        <div style={{
          ...styles.indicator,
          backgroundColor: 
            status === 'online' ? '#4CAF50' : 
            status === 'away' ? '#FFC107' : 
            status === 'offline' ? '#9E9E9E' : '#CCCCCC'
        }}></div>
        <span>Current Status: {status || 'Loading...'}</span>
      </div>
    </div>
  );
};

// Styles
const styles: StyleObject = {
  container: {
    fontFamily: 'Arial, sans-serif',
    maxWidth: '400px',
    margin: '20px auto',
    padding: '20px',
    borderRadius: '8px',
    boxShadow: '0 2px 10px rgba(0, 0, 0, 0.1)',
    backgroundColor: '#ffffff'
  },
  connectionIndicator: {
    marginBottom: '15px',
    fontSize: '14px'
  },
  connected: {
    color: '#4CAF50',
    fontWeight: 'bold'
  },
  disconnected: {
    color: '#F44336',
    fontWeight: 'bold'
  },
  dropdownContainer: {
    marginBottom: '15px',
    display: 'flex',
    alignItems: 'center'
  },
  label: {
    marginRight: '10px',
    fontWeight: 'bold'
  },
  select: {
    padding: '8px 12px',
    borderRadius: '4px',
    border: '1px solid #ddd',
    fontSize: '14px',
    flex: 1
  },
  loading: {
    marginLeft: '10px',
    fontSize: '14px',
    color: '#666'
  },
  message: {
    padding: '10px',
    borderRadius: '4px',
    marginBottom: '15px',
    fontSize: '14px'
  },
  successMessage: {
    backgroundColor: '#E8F5E9',
    color: '#2E7D32'
  },
  errorMessage: {
    backgroundColor: '#FFEBEE',
    color: '#C62828'
  },
  statusIndicator: {
    display: 'flex',
    alignItems: 'center',
    marginTop: '15px'
  },
  indicator: {
    width: '12px',
    height: '12px',
    borderRadius: '50%',
    marginRight: '8px'
  }
};

export default UserStatusDropdown;