// API Client - TugaPark v2.0
// Suporta JWT tokens, sessões e modo mock (VITE_MOCK=true)

import axios from 'axios';
import { mockHandlers, resetMockState } from './mock/handlers';
import { getMockSpots } from './mock/data';

const IS_MOCK = import.meta.env.VITE_MOCK === 'true';
const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').trim();
const TOKEN_KEY = 'tugapark_token';

// Funções para gerir o token JWT
export function setAuthToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function getAuthToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function clearAuthToken() {
  localStorage.removeItem(TOKEN_KEY);
}

function matchMockRoute(path, method) {
  const key = `${method} ${path}`;
  if (mockHandlers[key]) {
    return { handler: mockHandlers[key], params: {} };
  }

  const dynamicRoutes = Object.keys(mockHandlers).filter(k => k.includes(':'));
  for (const route of dynamicRoutes) {
    const [routeMethod, routePath] = route.split(' ');
    if (routeMethod !== method) continue;

    const routeParts = routePath.split('/');
    const pathParts = path.split('/');
    if (routeParts.length !== pathParts.length) continue;

    const params = {};
    let match = true;
    for (let i = 0; i < routeParts.length; i++) {
      if (routeParts[i].startsWith(':')) {
        params[routeParts[i].slice(1)] = pathParts[i];
      } else if (routeParts[i] !== pathParts[i]) {
        match = false;
        break;
      }
    }
    if (match) return { handler: mockHandlers[route], params };
  }

  return null;
}

/**
 * API wrapper com suporte a JWT tokens e modo mock
 * @param {string} path - Caminho da API
 * @param {object} options - Opções (method, body, headers)
 */
export async function api(path, options = {}) {
  if (IS_MOCK) {
    const method = (options.method || 'GET').toUpperCase();
    const matched = matchMockRoute(path, method);
    if (matched) {
      const body = options.body ? JSON.parse(options.body) : {};
      const result = matched.handler(matched.params, body);
      if (result instanceof Promise) return await result;
      return result;
    }
    throw new Error(`Mock: No handler for ${method} ${path}`);
  }

  try {
    const method = (options.method || 'GET').toLowerCase();
    const url = `${API_BASE}${path}`;

    const headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    };

    const token = getAuthToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const data = options.body ? JSON.parse(options.body) : undefined;

    const res = await axios({ url, method, headers, data, withCredentials: true });
    return res.data;
  } catch (e) {
    if (e?.response?.status === 401) clearAuthToken();
    const msg = e?.response?.data?.detail || e?.response?.data?.error || e?.message || 'Erro';
    throw new Error(msg);
  }
}

export function createMockWebSocket(url, onMessage) {
  const interval = setInterval(() => {
    const data = JSON.stringify({ type: 'spot_update', spots: getMockSpots() });
    onMessage({ data });
  }, 3000);

  return {
    close: () => clearInterval(interval),
    readyState: WebSocket.OPEN
  };
}

export function resetMock() {
  resetMockState();
}

// Funções de conveniência
export const apiGet = (path) => api(path);
export const apiPost = (path, data) => api(path, { method: 'POST', body: JSON.stringify(data) });
export const apiPut = (path, data) => api(path, { method: 'PUT', body: JSON.stringify(data) });
export const apiDelete = (path) => api(path, { method: 'DELETE' });
