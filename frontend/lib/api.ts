/**
 * Centralized API client for XAI-Chain backend.
 *
 * Reads from environment variables so the same code works in
 * local dev, Docker Compose, and production without changes:
 *
 *   NEXT_PUBLIC_API_URL  — backend base URL (default: http://localhost:8000)
 *   NEXT_PUBLIC_API_KEY  — X-API-Key header value (required in production)
 *
 * Usage:
 *   import { apiRequest, apiGet, apiPost } from '@/lib/api';
 *
 *   const data = await apiGet('/api/audit/');
 *   const result = await apiPost('/api/analyze/', { tx_hash, network });
 */

const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ||
  'http://localhost:8000';

const API_KEY = process.env.NEXT_PUBLIC_API_KEY || '';

/** Base fetch wrapper — adds auth header and base URL to every request. */
export async function apiRequest(
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(API_KEY ? { 'X-API-Key': API_KEY } : {}),
    ...(options.headers as Record<string, string> | undefined),
  };

  return fetch(`${API_URL}${path}`, { ...options, headers });
}

/**
 * Convenience: GET request, returns parsed JSON.
 * Throws an Error with the backend `detail` message on non-2xx.
 */
export async function apiGet<T = unknown>(path: string): Promise<T> {
  const res = await apiRequest(path, { method: 'GET' });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(
      (body as { detail?: string }).detail ||
        `API error ${res.status} on GET ${path}`
    );
  }
  return res.json() as Promise<T>;
}

/**
 * Convenience: POST request, returns parsed JSON.
 * Throws an Error with the backend `detail` message on non-2xx.
 */
export async function apiPost<T = unknown>(
  path: string,
  body: unknown
): Promise<T> {
  const res = await apiRequest(path, {
    method: 'POST',
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(
      (errBody as { detail?: string }).detail ||
        `API error ${res.status} on POST ${path}`
    );
  }
  return res.json() as Promise<T>;
}
