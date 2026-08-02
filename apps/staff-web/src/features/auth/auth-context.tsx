import { authStorage } from '@medical-platform/auth';
import { createContext, useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { apiFetch } from '../../shared/utilities/api';
import type { CurrentUser, TokenResponse } from './types';

type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated';

export interface AuthState {
  status: AuthStatus;
  user: CurrentUser | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  /**
   * Re-checks auth state against whatever is currently in authStorage.
   * Needed after any flow that writes tokens directly (e.g. organization
   * registration) without going through `login` — writing to localStorage
   * doesn't itself notify this context, so callers must trigger the refresh.
   */
  refreshSession: () => Promise<void>;
}

export const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [user, setUser] = useState<CurrentUser | null>(null);

  const loadCurrentUser = useCallback(async () => {
    if (!authStorage.get()) {
      setStatus('unauthenticated');
      return;
    }
    try {
      const me = await apiFetch<CurrentUser>('/api/v1/auth/me');
      setUser(me);
      setStatus('authenticated');
    } catch {
      // apiFetch already cleared storage and is redirecting to /login on a
      // hard auth failure; this covers any other unexpected error the same way.
      authStorage.clear();
      setUser(null);
      setStatus('unauthenticated');
    }
  }, []);

  useEffect(() => {
    void loadCurrentUser();
  }, [loadCurrentUser]);

  const login = useCallback(
    async (email: string, password: string) => {
      const tokens = await apiFetch<TokenResponse>('/api/v1/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      authStorage.set({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token });
      await loadCurrentUser();
    },
    [loadCurrentUser],
  );

  const logout = useCallback(async () => {
    const session = authStorage.get();
    if (session) {
      try {
        await apiFetch('/api/v1/auth/logout', {
          method: 'POST',
          body: JSON.stringify({ refresh_token: session.refreshToken }),
        });
      } catch {
        // Best-effort revoke — clearing local storage below is what actually
        // ends the session on this device regardless of whether it succeeded.
      }
    }
    authStorage.clear();
    setUser(null);
    setStatus('unauthenticated');
  }, []);

  const value = useMemo<AuthState>(
    () => ({ status, user, login, logout, refreshSession: loadCurrentUser }),
    [status, user, login, logout, loadCurrentUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
