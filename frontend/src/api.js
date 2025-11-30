// Determines the base URL for API calls.
// - In development, default to http://localhost:8000 (AI_SE2 FastAPI backend) if not provided.
// - In production, default to same-origin ('') so the frontend can be served behind the same domain/proxy.
const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').trim();

import axios from 'axios';

/**
 * Small Axios wrapper for JSON APIs with friendly error messages.
 * AI_SE2 uses session-based authentication (cookies), not JWT tokens.
 * @param {string} path - The API path, e.g. '/api/reservations'
 * @param {RequestInit} options - Fetch-like options (method, headers, body...)
 */
export async function api(path, options = {}) {
    try {
        const method = (options.method || 'GET').toLowerCase();
        const url = `${API_BASE}${path}`;
        const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
        const data = options.body ? JSON.parse(options.body) : undefined;
        // Enable credentials to send/receive session cookies
        const res = await axios({ url, method, headers, data, withCredentials: true });
        return res.data;
    } catch (e) {
        const msg = e?.response?.data?.detail || e?.response?.data?.error || e?.message || 'Erro';
        throw new Error(msg);
    }
}
