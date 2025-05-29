import type { User } from '../types/userType';

const API_BASE_URL = 'http://localhost:8001';

export const profileEditAPI = {
	async getProfile(token: string): Promise<User> {
		const response = await fetch(`${API_BASE_URL}/users/me`, {
			method: 'GET',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`,
			},
		});
		if (!response.ok) {
			throw new Error('Failed to fetch user profile');
		}
		return response.json();
	},

	async updateProfile(
		data: { email?: string; display_name?: string; profile_picture?: string },
		token: string
	): Promise<void> {
		const response = await fetch(`${API_BASE_URL}/users/me`, {
			method: 'PUT',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`,
			},
			body: JSON.stringify(data),
		});
		if (!response.ok) {
			throw new Error('Failed to update user profile');
		}
	},
};
