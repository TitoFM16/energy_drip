import { useState } from 'react';
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom';
import { useResetPassword } from '../../features/auth/use-reset-password';

export function ResetPasswordPage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const resetPassword = useResetPassword();
  const [newPassword, setNewPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await resetPassword.mutateAsync({ token: token!, new_password: newPassword });
      navigate('/login', { replace: true, state: { passwordResetSuccess: true } });
    } catch {
      setError('Este enlace no es válido o ya expiró. Solicita uno nuevo.');
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="mb-6 text-xl font-semibold text-slate-900">Nueva contraseña</h1>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
            Nueva contraseña
            <input
              type="password"
              required
              minLength={8}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </label>
          {error && (
            <p className="text-sm text-red-600">
              {error}{' '}
              <Link to="/forgot-password" className="underline">
                Pedir otro enlace
              </Link>
            </p>
          )}
          <button
            type="submit"
            disabled={resetPassword.isPending}
            className="mt-2 rounded-lg bg-slate-900 py-2.5 text-sm font-semibold text-white disabled:opacity-40"
          >
            {resetPassword.isPending ? 'Guardando...' : 'Guardar contraseña'}
          </button>
        </form>
      </div>
    </div>
  );
}
