// API service for authentication and other API calls

import { io, Socket } from 'socket.io-client';

const API_BASE_URL = 'http://localhost:8001';
const SOCKET_URL = 'http://localhost:8000';

interface User {
  id: string;
  username: string;
  email: string;
}

interface AuthResponse {
  error: boolean;
  message?: string;
  user?: User;
}

interface LoginResponse extends AuthResponse {
  token?: string;
  token_type?: string;
  expires_at?: string;
}

type AuthPromiseValue = AuthResponse | LoginResponse;

// Helper function to get headers with authentication
const getAuthHeaders = (providedToken?: string) => {
  const token = providedToken || localStorage.getItem('auth_token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
  };
};

class AuthService {
  private socket: Socket | null = null;
  private authPromises: Map<string, {
    resolve: (value: AuthPromiseValue) => void;
    reject: (reason: Error) => void;
  }> = new Map();

  constructor() {
    this.connect();
  }

  private connect() {
    this.socket = io(SOCKET_URL);

    // Set up auth event handlers
    this.socket.on('auth:register:success', (response) => {
      const resolve = this.authPromises.get('register')?.resolve;
      if (resolve) {
        resolve(response);
        this.authPromises.delete('register');
      }
    });

    this.socket.on('auth:register:error', (error) => {
      const reject = this.authPromises.get('register')?.reject;
      if (reject) {
        reject(new Error(error.message || 'Registration failed'));
        this.authPromises.delete('register');
      }
    });

    this.socket.on('auth:login:success', (response) => {
      // Store the token
      if (response.token) {
        localStorage.setItem('auth_token', response.token);
      }
      const resolve = this.authPromises.get('login')?.resolve;
      if (resolve) {
        resolve(response);
        this.authPromises.delete('login');
      }
    });

    this.socket.on('auth:login:error', (error) => {
      const reject = this.authPromises.get('login')?.reject;
      if (reject) {
        reject(new Error(error.message || 'Login failed'));
        this.authPromises.delete('login');
      }
    });

    this.socket.on('auth:logout:success', () => {
      localStorage.removeItem('auth_token');
      const resolve = this.authPromises.get('logout')?.resolve;
      if (resolve) {
        resolve({ error: false });
        this.authPromises.delete('logout');
      }
    });

    this.socket.on('auth:logout:error', (error) => {
      const reject = this.authPromises.get('logout')?.reject;
      if (reject) {
        reject(new Error(error.message || 'Logout failed'));
        this.authPromises.delete('logout');
      }
    });
  }

  async register(username: string, password: string, email: string): Promise<AuthResponse> {
    if (!this.socket?.connected) {
      throw new Error('Socket not connected');
    }

    return new Promise((resolve, reject) => {
      this.authPromises.set('register', { resolve, reject });
      this.socket!.emit('auth:register', { username, password, email });
    });
  }

  async login(username: string, password: string): Promise<LoginResponse> {
    if (!this.socket?.connected) {
      throw new Error('Socket not connected');
    }

    return new Promise((resolve, reject) => {
      this.authPromises.set('login', { resolve, reject });
      this.socket!.emit('auth:login', { username, password });
    });
  }

  async logout(): Promise<AuthResponse> {
    if (!this.socket?.connected) {
      throw new Error('Socket not connected');
    }

    return new Promise<AuthResponse>((resolve, reject) => {
      this.authPromises.set('logout', { resolve, reject });
      this.socket!.emit('auth:logout');
    });
  }

  async validateToken(token?: string): Promise<AuthResponse> {
    if (!this.socket?.connected) {
      throw new Error('Socket not connected');
    }

    return new Promise((resolve, reject) => {
      this.authPromises.set('validate', { resolve, reject });
      this.socket!.emit('auth:validate', { token });
    });
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }
}

// Create a singleton instance
const authService = new AuthService();

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

export default authService;