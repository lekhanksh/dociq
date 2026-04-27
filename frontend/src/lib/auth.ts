// Authentication API functions for DocIQ

export interface LoginRequest {
  email: string;
  password: string;
  company_slug: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    email: string;
    full_name: string | null;
    department: string;
    role: string;
    company_name: string;
  };
}

export interface UserResponse {
  id: string;
  email: string;
  full_name: string | null;
  department: string;
  role: string;
  company_name: string;
}

// Get base URL from API config
const getBaseUrl = () => {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  
  const mode = import.meta.env.MODE;
  switch (mode) {
    case 'demo':
      return 'https://YOUR_EC2_PUBLIC_IP'; // Update after deployment
    case 'staging':
      return 'https://staging.your-domain.com';
    case 'production':
      return 'https://api.your-domain.com';
    default:
      return 'http://localhost:8000';
  }
};

const BASE_URL = getBaseUrl();

// Store token in localStorage
const TOKEN_KEY = 'auth_token';

export const getStoredToken = (): string | null => {
  return localStorage.getItem(TOKEN_KEY);
};

export const setStoredToken = (token: string): void => {
  localStorage.setItem(TOKEN_KEY, token);
};

export const clearStoredToken = (): void => {
  localStorage.removeItem(TOKEN_KEY);
};

// Authentication API calls
export const login = async (data: LoginRequest): Promise<LoginResponse> => {
  const response = await fetch(`${BASE_URL}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'Login failed');
  }

  const result = await response.json() as LoginResponse;
  setStoredToken(result.access_token);
  return result;
};

export const getCurrentUser = async (): Promise<UserResponse> => {
  const token = getStoredToken();
  if (!token) {
    throw new Error('No authentication token found');
  }

  const response = await fetch(`${BASE_URL}/auth/me`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      clearStoredToken();
      throw new Error('Authentication expired');
    }
    throw new Error('Failed to get user info');
  }

  return await response.json() as UserResponse;
};

export const refreshToken = async (): Promise<{ access_token: string }> => {
  const token = getStoredToken();
  if (!token) {
    throw new Error('No authentication token found');
  }

  const response = await fetch(`${BASE_URL}/auth/refresh`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    clearStoredToken();
    throw new Error('Token refresh failed');
  }

  const result = await response.json() as { access_token: string };
  setStoredToken(result.access_token);
  return result;
};

// API request helper with authentication
export const authenticatedFetch = async (url: string, options: RequestInit = {}): Promise<Response> => {
  const token = getStoredToken();
  if (!token) {
    throw new Error('No authentication token found');
  }

  const response = await fetch(`${BASE_URL}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...options.headers,
    },
  });

  if (response.status === 401) {
    clearStoredToken();
    window.location.href = '/login';
    throw new Error('Authentication expired');
  }

  return response;
};
