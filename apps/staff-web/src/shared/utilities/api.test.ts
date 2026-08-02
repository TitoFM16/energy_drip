import { beforeEach, describe, expect, it, vi } from 'vitest';
import { authStorage } from '@medical-platform/auth';
import { apiFetch } from './api';

vi.mock('@medical-platform/auth', () => ({
  authStorage: {
    get: vi.fn(),
    set: vi.fn(),
    setTokens: vi.fn(),
    clear: vi.fn(),
  },
}));

const mockFetch = vi.fn();

describe('apiFetch', () => {
  beforeEach(() => {
    mockFetch.mockReset();
    vi.stubGlobal('fetch', mockFetch);
    vi.stubGlobal('window', { location: { assign: vi.fn() } });
    vi.mocked(authStorage.get).mockReset();
    vi.mocked(authStorage.setTokens).mockReset();
    vi.mocked(authStorage.clear).mockReset();
  });

  it('attaches the Authorization header when a session exists', async () => {
    vi.mocked(authStorage.get).mockReturnValue({
      accessToken: 'access-1',
      refreshToken: 'refresh-1',
    });
    mockFetch.mockResolvedValueOnce(new Response(JSON.stringify({ ok: true }), { status: 200 }));

    await apiFetch('/api/v1/patients');

    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer access-1');
  });

  it('omits the Authorization header when there is no session', async () => {
    vi.mocked(authStorage.get).mockReturnValue(null);
    mockFetch.mockResolvedValueOnce(new Response('{}', { status: 200 }));

    await apiFetch('/api/v1/public/consents/abc');

    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>).Authorization).toBeUndefined();
  });

  it('retries exactly once after a silent refresh on 401', async () => {
    vi.mocked(authStorage.get).mockReturnValue({
      accessToken: 'expired',
      refreshToken: 'refresh-1',
    });
    mockFetch
      .mockResolvedValueOnce(new Response('unauthorized', { status: 401 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ access_token: 'new-access', refresh_token: 'new-refresh' }), {
          status: 200,
        }),
      )
      .mockResolvedValueOnce(new Response(JSON.stringify({ data: 'ok' }), { status: 200 }));

    const result = await apiFetch('/api/v1/patients');

    expect(result).toEqual({ data: 'ok' });
    expect(mockFetch).toHaveBeenCalledTimes(3);
    expect(authStorage.setTokens).toHaveBeenCalledWith('new-access', 'new-refresh');
  });

  it('clears the session and redirects to /login when refresh also fails', async () => {
    vi.mocked(authStorage.get).mockReturnValue({ accessToken: 'expired', refreshToken: 'stale' });
    mockFetch
      .mockResolvedValueOnce(new Response('unauthorized', { status: 401 }))
      .mockResolvedValueOnce(new Response('unauthorized', { status: 401 }));

    await expect(apiFetch('/api/v1/patients')).rejects.toThrow('Session expired');

    expect(authStorage.clear).toHaveBeenCalled();
    expect(window.location.assign).toHaveBeenCalledWith('/login');
  });

  it('throws a descriptive error for a non-ok, non-401 response', async () => {
    vi.mocked(authStorage.get).mockReturnValue(null);
    mockFetch.mockResolvedValueOnce(new Response('boom', { status: 500 }));

    await expect(apiFetch('/api/v1/patients')).rejects.toThrow(/failed \(500\)/);
  });

  it('returns undefined for a 204 No Content response', async () => {
    vi.mocked(authStorage.get).mockReturnValue(null);
    mockFetch.mockResolvedValueOnce(new Response(null, { status: 204 }));

    const result = await apiFetch('/api/v1/auth/logout', { method: 'POST' });
    expect(result).toBeUndefined();
  });
});
