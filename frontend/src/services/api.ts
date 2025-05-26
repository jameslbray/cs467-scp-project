// API service for authentication and other API calls
const API_BASE_URL = 'http://localhost:8001';

const getAuthHeaders = (providedToken?: string) => {
	const token = providedToken || localStorage.getItem('auth_token');
	return {
		'Content-Type': 'application/json',
		...(token ? { Authorization: `Bearer ${token}` } : {}),
	};
};

// Authentication API calls
export const authApi = {
	login: async (username: string, password: string) => {
		const params = new URLSearchParams();
		params.append('username', username);
		params.append('password', password);

		const response = await fetch(`${API_BASE_URL}/token`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/x-www-form-urlencoded',
			},
			body: params.toString(),
		});

		if (!response.ok) {
			const errorData = await response.json();
			throw new Error(errorData.message || 'Login failed');
		}

		return response.json();
	},

	register: async (username: string, password: string, email: string) => {
		const requestData = { username, password, email };

		const response = await fetch(`${API_BASE_URL}/register`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify(requestData),
		});

		if (!response.ok) {
			const errorData = await response.json();
			console.error('Registration error:', errorData);
			throw new Error(errorData.detail || 'Registration failed');
		}

		return response.json();
	},

	validateToken: async (tokenToValidate?: string) => {
		const response = await fetch(`${API_BASE_URL}/users/me`, {
			method: 'GET',
			headers: getAuthHeaders(tokenToValidate),
		});

		if (!response.ok) {
			throw new Error('Token validation failed');
		}

		return response.json();
	},

	logout: async () => {
		const response = await fetch(`${API_BASE_URL}/logout`, {
			method: 'POST',
			headers: getAuthHeaders(),
		});

		if (!response.ok) {
			console.error('Logout failed:', await response.text());
		}

		return response.ok;
	},

	// Password reset: request reset link
	requestPasswordReset: async (email: string) => {
		const response = await fetch(`${API_BASE_URL}/password-reset/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ email }),
		});

		if (!response.ok) {
			const errorData = await response.json();
			throw new Error(errorData.detail || 'Failed to request password reset');
		}

		return response.json();
	},

	// Password reset: confirm new password
	confirmPasswordReset: async (token: string, newPassword: string) => {
		const response = await fetch(`${API_BASE_URL}/password-reset-confirm/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ token, new_password: newPassword }),
		});

		if (!response.ok) {
			const errorData = await response.json();
			throw new Error(errorData.detail || 'Failed to reset password');
		}

		return response.json();
	},
};

// User API calls
export const userApi = {
	getProfile: async () => {
		const response = await fetch(`${API_BASE_URL}/profile`, {
			method: 'GET',
			headers: getAuthHeaders(),
		});

		if (!response.ok) {
			throw new Error('Failed to fetch user profile');
		}

		return response.json();
	},

	updateProfile: async (data: { username?: string; email?: string; profilePicture?: string }) => {
		const response = await fetch(`${API_BASE_URL}/profile`, {
			method: 'PUT',
			headers: getAuthHeaders(),
			body: JSON.stringify(data),
		});

		if (!response.ok) {
			const errorData = await response.json();
			throw new Error(errorData.message || 'Failed to update profile');
		}

		return response.json();
	},

	getUsersByIds: async (ids: string[]) => {
		if (!ids.length) return [];

		// Send as comma-separated values
		const response = await fetch(`${API_BASE_URL}/users/?user_ids=${ids.join(',')}`, {
			method: 'GET',
			headers: getAuthHeaders(),
		});

		if (!response.ok) {
			const errorData = await response.json();
			throw new Error(errorData.message || 'Failed to fetch users');
		}

		return response.json();
	},
};

// Chat/Room API calls
export const chatApi = {
	createRoom: async (data: {
		name: string;
		description?: string;
		is_private?: boolean;
		max_participants?: number | null;
		participant_ids: string[];
	}) => {
		const token = localStorage.getItem('auth_token');
		const response = await fetch('http://localhost:8004/rooms', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				...(token ? { Authorization: `Bearer ${token}` } : {}),
			},
			body: JSON.stringify(data),
		});
		if (!response.ok) {
			const errorData = await response.json();
			throw new Error(errorData.detail || 'Failed to create room');
		}
		return response.json();
	},
};
