/**
 * The single HTTP entry point to the Fikisha API.
 *
 * Design (Phase 1 api-architecture + security-architecture):
 *  - The short-lived access token lives in memory only — never localStorage.
 *    A page reload starts unauthenticated and silently re-derives a session
 *    from the HttpOnly refresh cookie (`credentials: 'include'`).
 *  - Every error is parsed as RFC 9457 problem+json into `ApiError`.
 *  - A single transparent refresh-and-retry runs on a 401. A second 401
 *    (or a failed refresh) clears the session and notifies subscribers.
 */

import { env } from './env';
import { ApiError, isProblemDetail, type ProblemDetail } from './problem';

let accessToken: string | null = null;
const authLostListeners = new Set<() => void>();

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

export function onAuthLost(listener: () => void): () => void {
  authLostListeners.add(listener);
  return () => authLostListeners.delete(listener);
}

function notifyAuthLost(): void {
  setAccessToken(null);
  for (const listener of authLostListeners) listener();
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';
  body?: unknown;
  /** Attach the bearer token (default true). */
  auth?: boolean;
  /** Attempt one refresh-and-retry on a 401 (default true). */
  retryOnUnauthorized?: boolean;
  signal?: AbortSignal;
  /**
   * Sent as `Idempotency-Key` — required by the backend for job-creation and
   * every lifecycle-transition call (submit, cancel, assign, custody
   * confirms, negotiation accept, dispute resolve; see phase-2d-api.md §1).
   * Generate once per user-initiated attempt (e.g. `crypto.randomUUID()`)
   * and reuse it across a retry of the *same* attempt — a fresh key per
   * retry defeats the point.
   */
  idempotencyKey?: string;
}

async function parseBody(response: Response): Promise<unknown> {
  if (response.status === 204) return null;
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

/**
 * Single-flight refresh (Design Phase 7 P-15). The backend rotates the
 * refresh cookie on every use and treats a reused (already spent) cookie as
 * theft, revoking the whole session. Two requests that 401 at the same time
 * (several queries after the access token expires, or React StrictMode's
 * double start-up in dev) must therefore share one refresh, not each send
 * the same cookie.
 */
let refreshInFlight: Promise<boolean> | null = null;

function refreshSession(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = doRefresh().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

async function doRefresh(): Promise<boolean> {
  try {
    const response = await fetch(`${env.apiBaseUrl}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!response.ok) return false;
    const data = (await parseBody(response)) as { access_token?: string } | null;
    if (data?.access_token) {
      setAccessToken(data.access_token);
      return true;
    }
    return false;
  } catch {
    return false;
  }
}

export async function apiRequest<T = unknown>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const {
    method = 'GET',
    body,
    auth = true,
    retryOnUnauthorized = true,
    signal,
    idempotencyKey,
  } = options;
  const isForm = typeof FormData !== 'undefined' && body instanceof FormData;

  const headers: Record<string, string> = { Accept: 'application/json' };
  if (body !== undefined && !isForm) headers['Content-Type'] = 'application/json';
  const tokenSent = auth ? accessToken : null;
  if (tokenSent) headers.Authorization = `Bearer ${tokenSent}`;
  if (idempotencyKey) headers['Idempotency-Key'] = idempotencyKey;

  let response: Response;
  try {
    response = await fetch(`${env.apiBaseUrl}${path}`, {
      method,
      headers,
      credentials: 'include',
      body: body === undefined ? undefined : isForm ? (body as FormData) : JSON.stringify(body),
      signal,
    });
  } catch (cause) {
    throw new ApiError(undefined, 0, cause instanceof Error ? cause.message : 'Network error');
  }

  if (response.status === 401 && auth && retryOnUnauthorized) {
    // Another request refreshed while this one was in flight: just retry
    // with the new token rather than spending the cookie again.
    const refreshed = (accessToken !== null && accessToken !== tokenSent) || (await refreshSession());
    if (refreshed) {
      return apiRequest<T>(path, { ...options, retryOnUnauthorized: false });
    }
    notifyAuthLost();
  }

  const parsed = await parseBody(response);

  if (!response.ok) {
    const problem: ProblemDetail | undefined = isProblemDetail(parsed) ? parsed : undefined;
    throw new ApiError(problem, response.status, `Request failed (${response.status})`);
  }

  return parsed as T;
}

/** Fetch a binary response (e.g. verification evidence) as a Blob, with auth. */
export async function fetchBlob(path: string): Promise<Blob> {
  const headers: Record<string, string> = {};
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  let response = await fetch(`${env.apiBaseUrl}${path}`, {
    headers,
    credentials: 'include',
  });
  if (response.status === 401 && (await refreshSession())) {
    const retryHeaders: Record<string, string> = {};
    if (accessToken) retryHeaders.Authorization = `Bearer ${accessToken}`;
    response = await fetch(`${env.apiBaseUrl}${path}`, {
      headers: retryHeaders,
      credentials: 'include',
    });
  }
  if (!response.ok) {
    throw new ApiError(undefined, response.status, `Download failed (${response.status})`);
  }
  return response.blob();
}
