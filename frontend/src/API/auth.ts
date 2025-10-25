/**
 * Authentication API functions
 */

const API_BASE_URL = 'http://localhost:5000/api';

export interface User {
  username: string;
  role: string;
  created_at?: number;
  last_login?: number;
}

export interface LoginResponse {
  success: boolean;
  user?: User;
  error?: string;
}

export interface SessionResponse {
  authenticated: boolean;
  user?: User;
}

/**
 * Login with username and password
 */
export const login = async (username: string, password: string): Promise<LoginResponse> => {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include', // Include cookies for session
      body: JSON.stringify({ username, password }),
    });

    const data = await response.json();

    if (response.ok) {
      return { success: true, user: data.user };
    } else {
      return { success: false, error: data.error || 'Login failed' };
    }
  } catch (error) {
    return { success: false, error: 'Network error' };
  }
};

/**
 * Logout current user
 */
export const logout = async (): Promise<{ success: boolean; error?: string }> => {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    });

    const data = await response.json();

    if (response.ok) {
      return { success: true };
    } else {
      return { success: false, error: data.error || 'Logout failed' };
    }
  } catch (error) {
    return { success: false, error: 'Network error' };
  }
};

/**
 * Check if user is authenticated
 */
export const checkSession = async (): Promise<SessionResponse> => {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/session`, {
      method: 'GET',
      credentials: 'include',
    });

    const data = await response.json();
    return data;
  } catch (error) {
    return { authenticated: false };
  }
};

/**
 * Get current user information
 */
export const getCurrentUser = async (): Promise<User | null> => {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
      method: 'GET',
      credentials: 'include',
    });

    if (response.ok) {
      const data = await response.json();
      return data;
    } else {
      return null;
    }
  } catch (error) {
    return null;
  }
};
