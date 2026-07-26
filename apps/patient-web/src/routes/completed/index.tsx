import { useLocation } from 'react-router-dom';

const MESSAGES: Record<string, { title: string; body: string }> = {
  eligible: {
    title: 'Todo listo',
    body: 'Tu consentimiento fue registrado. Te esperamos en tu cita.',
  },
  requires_manual_review: {
    title: 'Recibimos tus respuestas',
    body: 'Un profesional de la clínica revisará tus respuestas antes de tu cita y se pondrá en contacto contigo.',
  },
  not_eligible: {
    title: 'Necesitamos hablar contigo',
    body: 'Según tus respuestas, la clínica se comunicará contigo antes de confirmar el tratamiento.',
  },
};

export function CompletedPage() {
  const location = useLocation();
  const eligibilityResult = (location.state as { eligibilityResult?: string } | null)
    ?.eligibilityResult;
  const message = MESSAGES[eligibilityResult ?? ''] ?? MESSAGES.requires_manual_review;

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 text-center">
      <h1 className="text-xl font-bold text-slate-900">{message.title}</h1>
      <p className="text-slate-600">{message.body}</p>
    </div>
  );
}
