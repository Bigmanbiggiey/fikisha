import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { apiRequest, onAuthLost, setAccessToken } from './apiClient';
import { ApiError } from './problem';

function jsonResponse(body: unknown, init: ResponseInit & { contentType?: string } = {}): Response {
  const { contentType = 'application/json', ...rest } = init;
  return new Response(body === null ? null : JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': contentType },
    ...rest,
  });
}

describe('apiRequest', () => {
  beforeEach(() => {
    setAccessToken(null);
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns parsed JSON on success and attaches the bearer token', async () => {
    setAccessToken('tok-123');
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({ ok: true }));

    const data = await apiRequest<{ ok: boolean }>('/thing');

    expect(data).toEqual({ ok: true });
    const headers = new Headers(fetchMock.mock.calls[0]![1]!.headers as HeadersInit);
    expect(headers.get('Authorization')).toBe('Bearer tok-123');
  });

  it('throws a typed ApiError carrying the problem+json code', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      jsonResponse(
        { code: 'otp.invalid', status: 401, title: 'Unauthorized', detail: 'bad code' },
        { status: 401, contentType: 'application/problem+json' },
      ),
    );

    // auth:false so no refresh/retry path
    const error = await apiRequest('/auth/otp/verify', { method: 'POST', auth: false }).catch(
      (e: unknown) => e,
    );
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe('otp.invalid');
    expect((error as ApiError).status).toBe(401);
  });

  it('refreshes once on a 401 and retries the original request', async () => {
    setAccessToken('stale');
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(
        jsonResponse({ code: 'auth.token_expired', status: 401 }, { status: 401 }),
      )
      .mockResolvedValueOnce(jsonResponse({ access_token: 'fresh' }))
      .mockResolvedValueOnce(jsonResponse({ me: true }));

    const data = await apiRequest<{ me: boolean }>('/me');

    expect(data).toEqual({ me: true });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[1]![0]).toContain('/auth/refresh');
  });

  it('notifies subscribers and gives up when refresh fails', async () => {
    setAccessToken('stale');
    const lost = vi.fn();
    const unsubscribe = onAuthLost(lost);

    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse({ code: 'auth.token_expired' }, { status: 401 }))
      .mockResolvedValueOnce(jsonResponse({ detail: 'nope' }, { status: 401 }));

    await expect(apiRequest('/me')).rejects.toBeInstanceOf(ApiError);
    expect(lost).toHaveBeenCalledOnce();
    unsubscribe();
  });
});
