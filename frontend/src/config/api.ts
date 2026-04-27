// API Configuration for DocIQ Frontend
export const API_CONFIG = {
  development: {
    baseURL: 'http://localhost:8000',
    timeout: 10000,
  },
  demo: {
    baseURL: 'https://YOUR_EC2_PUBLIC_IP', // Update after deployment
    timeout: 10000,
  },
  staging: {
    baseURL: 'https://staging.your-domain.com',
    timeout: 10000,
  },
  production: {
    baseURL: 'https://api.your-domain.com',
    timeout: 10000,
  }
};

// Get current environment config
export const getCurrentConfig = () => {
  const env = import.meta.env.MODE || 'development';
  return API_CONFIG[env] || API_CONFIG.development;
};

// API endpoints
export const API_ENDPOINTS = {
  auth: {
    login: '/auth/login',
    me: '/auth/me',
    refresh: '/auth/refresh',
  },
  query: '/query',
  upload: '/upload',
  collections: '/collections/info',
  admin: {
    users: '/admin/users',
    companies: '/admin/companies',
  }
} as const;
