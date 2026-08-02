import { Button, ErrorText, TextField } from '@medical-platform/ui';
import { useState } from 'react';
import { Navigate, useNavigate, useParams } from 'react-router-dom';
import { authStorage } from '@medical-platform/auth';
import { useAcceptInvite } from '../../features/auth/use-accept-invite';
import { useAuth } from '../../features/auth/use-auth';

export function AcceptInvitePage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const { refreshSession } = useAuth();
  const acceptInvite = useAcceptInvite();
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const tokens = await acceptInvite.mutateAsync({
        token: token!,
        full_name: fullName,
        password,
      });
      authStorage.set({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token });
      await refreshSession();
      navigate('/', { replace: true });
    } catch {
      setError('Esta invitación no es válida o ya expiró. Pide una nueva a tu administrador.');
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="mb-2 text-xl font-semibold text-slate-900">Completa tu cuenta</h1>
        <p className="mb-6 text-sm text-slate-500">
          Elige tu nombre y una contraseña para activar tu acceso.
        </p>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <TextField
            label="Nombre completo"
            type="text"
            required
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
          />
          <TextField
            label="Contraseña"
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error && <ErrorText>{error}</ErrorText>}
          <Button type="submit" disabled={acceptInvite.isPending} className="mt-2">
            {acceptInvite.isPending ? 'Activando...' : 'Activar cuenta'}
          </Button>
        </form>
      </div>
    </div>
  );
}
