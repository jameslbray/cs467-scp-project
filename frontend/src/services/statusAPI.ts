import { StatusType } from '../types';

const PRESENCE_BASE_URL = 'http://localhost:8003';
const FETCH_TIMEOUT = 5000; // 5 second timeout for API calls
const FALLBACK_STATUS: StatusResponse = {
    user_id: '',
    status: StatusType.OFFLINE,
    last_seen: new Date().toISOString(),
    additional_info: null
};

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
        try {
            // Create an AbortController for timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT);
            
            const response = await fetch(`${PRESENCE_BASE_URL}/api/status/${userId}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);

            if (response.status !== 200) {
                console.warn(`Non-200 status code from status API: ${response.status} ${response.statusText}`);
                return { ...FALLBACK_STATUS, user_id: userId };
            }

            return response.json();
        } catch (error) {
            console.error('Error fetching user status:', error);
            // Return fallback status instead of throwing
            return { ...FALLBACK_STATUS, user_id: userId };
        }
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
            console.error(`Invalid status value: ${statusData.status}`);
            return { ...FALLBACK_STATUS, user_id: userId };
        }

        try {
            // Create an AbortController for timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT);
            
            const response = await fetch(`${PRESENCE_BASE_URL}/api/status/${userId}`, {
                method: 'PUT',
                body: JSON.stringify(statusData),
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);

            if (!response.ok) {
                try {
                    const errorData = await response.json();
                    console.error('Updating status error:', errorData);
                } catch (e) {
                    console.error(`Status update failed ${e}, could not parse error response`, e);
                }
                // Return a fallback with the intended status rather than failing
                return { 
                    ...FALLBACK_STATUS, 
                    user_id: userId,
                    status: statusData.status,
                    additional_info: statusData.additional_info
                };
            }

            return response.json();
        } catch (error) {
            console.error('Error updating user status:', error);
            // Return fallback status with the intended update
            return { 
                ...FALLBACK_STATUS, 
                user_id: userId,
                status: statusData.status,
                additional_info: statusData.additional_info
            };
        }
    }
};