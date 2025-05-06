import { StatusType } from '../types';

const PRESENCE_BASE_URL = 'http://localhost:8003';

export interface StatusUpdate {
    status: StatusType;
    additional_info: string | null;
}

export interface StatusResponse {
    user_id: string;
    status: StatusType;
    last_seen: string;
    additional_info: string | null;
}

export const StatusAPI = {
    /**
     * Get a user's current status
     */
    getUserStatus: async (
        userId: string, 
        token: string
    ): Promise<StatusResponse> => {
        const response = await fetch(`${PRESENCE_BASE_URL}/api/status/${userId}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
        });

        if (response.status !== 200) {
            throw new Error(`Error fetching status: ${response.statusText}`);
        }

        return response.json();
    },

    /**
     * Update a user's status
     */
    updateUserStatus: async (
        userId: string,
        statusData: StatusUpdate,
        token: string
    ): Promise<StatusResponse> => {
        if (!Object.values(StatusType).includes(statusData.status)) {
            throw new Error(`Invalid status value: ${statusData.status}`);
        }

        const response = await fetch(`${PRESENCE_BASE_URL}/api/status/${userId}`, {
            method: 'PUT',
            body: JSON.stringify(statusData),
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            const errorData = await response.json();
            console.error('Updating status error:', errorData);
            throw new Error(errorData.detail || 'Status Update failed');
        }

        return response.json();
    }
};