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

  it('attaches Idempotency-Key when given, and omits it when not', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse({ ok: true }))
      .mockResolvedValueOnce(jsonResponse({ ok: true }));

    await apiRequest('/jobs/1/submit', { method: 'POST', idempotencyKey: 'key-abc' });
    const withKey = new Headers(fetchMock.mock.calls[0]![1]!.headers as HeadersInit);
    expect(withKey.get('Idempotency-Key')).toBe('key-abc');

    await apiRequest('/jobs/1', {});
    const withoutKey = new Headers(fetchMock.mock.calls[1]![1]!.headers as HeadersInit);
    expect(withoutKey.has('Idempotency-Key')).toBe(false);
  });

  it('shares one refresh between requests that 401 at the same time (P-15)', async () => {
    // The backend rotates the refresh cookie and revokes the session if a
    // spent one is reused, so two parallel refreshes would sign the user out.
    setAccessToken('expired');
    let refreshes = 0;
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/auth/refresh')) {
        refreshes += 1;
        await new Promise((r) => setTimeout(r, 10));
        return jsonResponse({ access_token: 'fresh' });
      }
      const auth = new Headers(init?.headers as HeadersInit).get('Authorization');
      return auth === 'Bearer fresh' ? jsonResponse({ url }) : jsonResponse({}, { status: 401 });
    });

    const results = await Promise.all([apiRequest('/a'), apiRequest('/b'), apiRequest('/c')]);

    expect(refreshes).toBe(1);
    expect(results).toHaveLength(3);
  });

  it('retries with the new token, without refreshing, when another request already refreshed', async () => {
    setAccessToken('old');
    let refreshes = 0;
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      if (String(input).endsWith('/auth/refresh')) {
        refreshes += 1;
        return jsonResponse({ access_token: 'unused' });
      }
      const auth = new Headers(init?.headers as HeadersInit).get('Authorization');
      if (auth === 'Bearer old') {
        // the token changes while this request is in flight
        setAccessToken('new');
        return jsonResponse({}, { status: 401 });
      }
      return jsonResponse({ ok: auth });
    });

    await expect(apiRequest('/x')).resolves.toEqual({ ok: 'Bearer new' });
    expect(refreshes).toBe(0);
  });
});
