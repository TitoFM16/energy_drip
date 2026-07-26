const TOKEN_KEY = 'medical_platform_access_token';

/**
 * Staff-app token storage only. The patient consent app never stores a
 * long-lived session — its single-use link token lives in the URL and is
 * never persisted client-side.
 */
export const tokenStorage = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};
