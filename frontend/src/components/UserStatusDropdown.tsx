import React, { useState, useEffect } from 'react';
import { StatusType } from '../types'; // ServerEvents, UserStatus, ClientEvents
import { useAuth } from '../contexts/auth/index.tsx';

const API_BASE_URL = 'http://localhost:8003';

// Style types
type StyleObject = Record<string, React.CSSProperties>;

const UserStatusDropdown: React.FC = () => {
  const [status, setStatus] = useState<StatusType>(StatusType.OFFLINE);

  const { user, token } = useAuth();

  // Load previous status from storage
  const loadStatus = async () => {
    if (!user) {
      console.error('User is null. Cannot fetch status.');
      return;
    }

    const response = await fetch(`${API_BASE_URL}/api/status/${user.id}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
    });
    const prevStatus = await response.json();

    if (response.status !== 200) {
      console.error('Error fetching status:', response.statusText);
      return;
    }
    if (prevStatus.status) {
      setStatus(prevStatus.status as StatusType);
    }
    console.log('Setting status to:', prevStatus.status);
  }

  const sendStatusUpdate = async (newStatus: StatusType) => {
    if (!user) {
      console.error('User is null. Cannot fetch status.');
      return;
    }

    console.log("User: ", user);
    const requestBody = {
      status: newStatus, 
      additional_info: user.username,
    };

    const response = await fetch(`${API_BASE_URL}/api/status/${user.id}`, {
      method: 'put',
      body: JSON.stringify(requestBody),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    console.log('Response:', response);
    if (response.status === 201 || response.status === 200) {
      alert(`Successfully changed ${status}!`);
    } else {
      alert(`Problem adding item. Response status = ${response.status}`);
    }
  };


  useEffect(() => {
    loadStatus();
  }, []);


  // const handleStatusChange = (e: React.ChangeEvent<HTMLSelectElement>): void => {
  //   const newStatus = e.target.value as StatusType;
  //   setStatus(newStatus);
  //   setIsLoading(true);
  //   setMessage('');

  //   if (socket && socket.connected) {
  //     // Use socket to update status based on your presence/events.py
  //     socket.emit(ClientEvents.UPDATE_STATUS, {
  //       status: newStatus
  //     });
  //   } else {
  //     // Fallback if socket is not connected
  //     setIsLoading(false);
  //     setMessage('Error: Not connected to server');
  //   }
  // };

  const handleStatusChange = (e: React.ChangeEvent<HTMLSelectElement>): void => {
    const newStatus = e.target.value as StatusType;
    setStatus(newStatus);
    console.log('Selected status:', newStatus);
    sendStatusUpdate(newStatus);

  }

  return (
    <div className="status-dropdown-container" style={styles.container}>
      <h2>User Status Updater {user ? `(User ID: ${user.id})` : '(No User Logged In)'}</h2>
      <div style={styles.connectionIndicator}>
        {user ?
          <span style={styles.connected}>Logged in</span> :
          <span style={styles.disconnected}>Not logged in</span>
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
          style={styles.select}
        >
          <option value="" disabled>Select status...</option>
          <option value="online">Online</option>
          <option value="away">Away</option>
          <option value="offline">Offline</option>
        </select>
      </div>
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
    </div >
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