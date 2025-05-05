import React from 'react';
import { StatusType } from '../types.tsx'; // ServerEvents, UserStatus, ClientEvents
import { useAuth } from '../contexts/auth/index.tsx';
import { useUserStatus } from '../hooks/useUserStatus.ts';

// Style types
type StyleObject = Record<string, React.CSSProperties>;

const UserStatusDropdown: React.FC = () => {
  const { user } = useAuth();
  const { status, isLoading, error, updateStatus } = useUserStatus(); // message

  const handleStatusChange = (e: React.ChangeEvent<HTMLSelectElement>): void => {
    const newStatus = e.target.value as StatusType;
    updateStatus(newStatus);
  };

  return (
    <div className="status-dropdown-container">
      <h2>User Status Updater {user ? `(User ID: ${user.id})` : '(No User Logged In)'}</h2>

      <div>
        <label htmlFor="status-select" style={styles.label}>
          Status:
        </label>
        <select
          id="status-select"
          value={status}
          onChange={handleStatusChange}
        >
          <option value="online">Online</option>
          <option value="away">Away</option>
          <option value="offline">Offline</option>
        </select>
      </div>

      <div>
        <div style={{
          ...styles.indicator,
          backgroundColor:
            status === 'online' ? '#4CAF50' :
              status === 'away' ? '#FFC107' :
                status === 'offline' ? '#9E9E9E' : '#CCCCCC'
        }}></div>
        <span>Current Status: { error ? error : isLoading ? 'Loading...' : status }</span>
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