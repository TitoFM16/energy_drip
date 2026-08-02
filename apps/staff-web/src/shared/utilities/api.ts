import { authStorage } from '@medical-platform/auth';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

let inFlightRefresh: Promise<boolean> | null = null;

async function refreshAccessTokenOnce(): Promise<boolean> {
  inFlightRefresh ??= doRefresh().finally(() => {
    inFlightRefresh = null;
  });
  return inFlightRefresh;
}

async function doRefresh(): Promise<boolean> {
  const session = authStorage.get();
  if (!session) return false;
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: session.refreshToken }),
  });
  if (!response.ok) return false;
  const body = (await response.json()) as { access_token: string; refresh_token: string };
  authStorage.setTokens(body.access_token, body.refresh_token);
  return true;
}

function buildHeaders(init?: RequestInit): HeadersInit {
  const session = authStorage.get();
  return {
    'Content-Type': 'application/json',
    ...(session ? { Authorization: `Bearer ${session.accessToken}` } : {}),
    ...init?.headers,
  };
}

/**
 * Fetch wrapper shared by every staff-web data hook. Attaches the stored
 * access token, and on a 401 attempts exactly one silent refresh (deduped
 * across concurrent callers) before giving up and sending the user back to
 * /login — so an expired token surfaces as a redirect, not scattered 401s
 * across whichever queries happened to be in flight.
 */
export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers: buildHeaders(init) });

  if (response.status === 401 && authStorage.get()) {
    const refreshed = await refreshAccessTokenOnce();
    if (refreshed) {
      response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers: buildHeaders(init) });
    } else {
      authStorage.clear();
      window.location.assign('/login');
      throw new Error('Session expired');
    }
  }

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`API request to ${path} failed (${response.status}): ${body}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}
