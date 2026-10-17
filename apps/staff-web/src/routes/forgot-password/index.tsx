import { Link } from 'react-router-dom';

export function ForgotPasswordPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="mb-3 text-xl font-semibold text-slate-900">Recuperar acceso</h1>
        <p className="mb-4 text-sm leading-relaxed text-slate-600">
          Contacta al administrador de la clínica para restablecer tu contraseña. Indícale el correo
          que utilizas para iniciar sesión.
        </p>
        <p className="mb-6 text-sm leading-relaxed text-slate-600">
          Si eres el propietario, solicita la recuperación a la persona que administra la
          instalación, siguiendo el procedimiento de recuperación de acceso.
        </p>
        <Link
          to="/login"
          className="inline-block rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white"
        >
          Volver a iniciar sesión
        </Link>
      </div>
    </div>
  );
}
