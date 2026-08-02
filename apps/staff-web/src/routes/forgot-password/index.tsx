import { Button, Callout, ErrorText, TextField } from '@medical-platform/ui';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useRequestPasswordReset } from '../../features/auth/use-request-password-reset';

export function ForgotPasswordPage() {
  const requestReset = useRequestPasswordReset();
  const [email, setEmail] = useState('');

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    await requestReset.mutateAsync(email);
  }

  const devToken = import.meta.env.DEV ? requestReset.data?.token : null;

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="mb-2 text-xl font-semibold text-slate-900">Recuperar contraseña</h1>
        <p className="mb-6 text-sm text-slate-500">
          Ingresa tu correo y te enviaremos un enlace para restablecer tu contraseña.
        </p>
        {requestReset.isSuccess ? (
          <div className="flex flex-col gap-4">
            <p className="text-sm text-slate-700">
              Si esa cuenta existe, te enviaremos un enlace para continuar.
            </p>
            {devToken && (
              <Callout variant="warning" className="text-xs">
                Solo en desarrollo —{' '}
                <Link to={`/reset-password/${devToken}`} className="underline">
                  continuar con el enlace de prueba
                </Link>
              </Callout>
            )}
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <TextField
              label="Correo electrónico"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            {requestReset.isError && (
              <ErrorText>No pudimos procesar la solicitud. Intenta de nuevo.</ErrorText>
            )}
            <Button type="submit" disabled={requestReset.isPending} className="mt-2">
              {requestReset.isPending ? 'Enviando...' : 'Enviar enlace'}
            </Button>
          </form>
        )}
        <p className="mt-6 text-center text-sm text-slate-500">
          <Link to="/login" className="font-medium text-slate-900 underline">
            Volver a iniciar sesión
          </Link>
        </p>
      </div>
    </div>
  );
}
