import React, { useState, useEffect } from 'react';
import { useSocketContext } from '../contexts/socket/socketContext';

interface Connection {
  sid: string;
  user_id?: string;
  room?: string;
  username?: string;
}

const ConnectedUsers: React.FC = () => {
  const { socket, isConnected } = useSocketContext();
  const [connections, setConnections] = useState<Connection[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!socket || !isConnected) return;

    const fetchConnections = () => {
      setLoading(true);
      setError(null);
      socket.emit('get_connections');
    };

    const handleConnectionsList = (data: Connection[]) => {
      setConnections(data);
      setLoading(false);
    };

    const handleRefreshConnections = () => {
      fetchConnections();
    };

    const handleError = (err: any) => {
      console.error('Connection error:', err);
      setError('Socket.IO connection failed');
      setLoading(false);
    };

    socket.on('connections_list', handleConnectionsList);
    socket.on('refresh_connections', handleRefreshConnections);
    socket.on('connect_error', handleError);

    fetchConnections();

    const interval = setInterval(() => {
    fetchConnections();
    }, 600000);  // Refresh every 10 minutes in case of missed events

    return () => {
      clearInterval(interval);
      socket.off('connections_list', handleConnectionsList);
      socket.off('refresh_connections', handleRefreshConnections);
      socket.off('connect_error', handleError);
    };
  }, [socket, isConnected]);

  return (
    <div className="bg-white dark:bg-gray-800 shadow-md rounded-md p-4 mt-4 max-w-3xl mx-auto">
      <h2 className="text-xl font-semibold mb-4 text-gray-800 dark:text-gray-100">
        Connected Users
      </h2>

      {loading && <p className="text-gray-500">Loading...</p>}
      {error && <p className="text-red-500">{error}</p>}

      {!loading && !error && connections.length === 0 && (
        <p className="text-gray-500">No users connected.</p>
      )}
      {!loading && !error && connections.length > 0 && (
        <table className="w-full text-sm text-left text-gray-600 dark:text-gray-300">
          <thead className="text-xs text-gray-700 uppercase bg-gray-100 dark:bg-gray-700 dark:text-gray-300">
            <tr>
              <th className="px-4 py-2">Username</th>
              <th className="px-4 py-2">Room</th>
            </tr>
          </thead>
          <tbody>
            {connections.map((conn) => (
              <tr key={conn.sid} className="border-b border-gray-200 dark:border-gray-600">
                <td className="px-4 py-2">{conn.username || '—'}</td>
                <td className="px-4 py-2">{conn.room || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default ConnectedUsers;
