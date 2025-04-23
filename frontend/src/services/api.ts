// API service for authentication and other API calls

const API_BASE_URL = 'http://localhost:8000';

// Helper function to get headers with authentication
const getAuthHeaders = () => {
  const token = localStorage.getItem('auth_token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
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
    console.log('Registration request data:', requestData);
    
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
  
  validateToken: async () => {
    const response = await fetch(`${API_BASE_URL}/users/me`, {
      method: 'GET',
      headers: getAuthHeaders(),
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
}; 