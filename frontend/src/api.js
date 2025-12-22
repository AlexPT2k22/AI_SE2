// API Client - TugaPark v2.0
// Suporta JWT tokens e sessões

import axios from 'axios';

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

/**
 * API wrapper com suporte a JWT tokens
 * @param {string} path - Caminho da API
 * @param {object} options - Opções (method, body, headers)
 */
export async function api(path, options = {}) {
 try {
 const method = (options.method || 'GET').toLowerCase();
 const url = `${API_BASE}${path}`;

 // Headers base
 const headers = {
 'Content-Type': 'application/json',
 ...(options.headers || {})
 };

 // Adicionar token JWT se existir
 const token = getAuthToken();
 if (token) {
 headers['Authorization'] = `Bearer ${token}`;
 }

 // Parse body se necessário
 const data = options.body ? JSON.parse(options.body) : undefined;

 // Fazer request
 const res = await axios({
 url,
 method,
 headers,
 data,
 withCredentials: true
 });

 return res.data;
 } catch (e) {
 // Se for 401, limpar token
 if (e?.response?.status === 401) {
 clearAuthToken();
 }

 const msg = e?.response?.data?.detail || e?.response?.data?.error || e?.message || 'Erro';
 throw new Error(msg);
 }
}

// Funções de conveniência para operações comuns
export const apiGet = (path) => api(path);
export const apiPost = (path, data) => api(path, { method: 'POST', body: JSON.stringify(data) });
export const apiPut = (path, data) => api(path, { method: 'PUT', body: JSON.stringify(data) });
export const apiDelete = (path) => api(path, { method: 'DELETE' });
