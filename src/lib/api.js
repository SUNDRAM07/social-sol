// Use environment variable or detect from current location
const getApiBaseUrl = () => {
  // Production: Use VITE_API_BASE_URL pointing to Railway backend
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL.replace(/\/$/, '');
  }
  // Development: Use localhost
  return 'http://localhost:8000';
};

export const API_BASE_URL = getApiBaseUrl();

export function apiUrl(path) {
  if (!path) return API_BASE_URL;
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_BASE_URL}${path.startsWith('/') ? '' : '/'}${path}`;
}

export function apiFetch(path, options = {}) {
  // Get auth token from localStorage
  const authData = localStorage.getItem('auth-storage');
  let token = null;

  if (authData) {
    try {
      const parsed = JSON.parse(authData);
      token = parsed.state?.token;
    } catch (e) {
      console.warn('Failed to parse auth data:', e);
    }
  }

  // Add auth header if token exists
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  return fetch(apiUrl(path), {
    ...options,
    headers,
  });
}


