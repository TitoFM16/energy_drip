const ACCESS_TOKEN_KEY = 'medical_platform_access_token';
const REFRESH_TOKEN_KEY = 'medical_platform_refresh_token';

export interface StoredSession {
  accessToken: string;
  refreshToken: string;
}

/**
 * Staff-app session storage only. The patient consent app never stores a
 * long-lived session — its single-use link token lives in the URL and is
 * never persisted client-side.
 *
 * This product has exactly one clinic, so there is no organization ID to
 * track alongside the tokens — every request is authorized by the access
 * token alone.
 */
export const authStorage = {
  get: (): StoredSession | null => {
    const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    if (!accessToken || !refreshToken) return null;
    return { accessToken, refreshToken };
  },
  set: (session: StoredSession) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, session.accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, session.refreshToken);
  },
  setTokens: (accessToken: string, refreshToken: string) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  },
  clear: () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
};
