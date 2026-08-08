import { Button } from '@medical-platform/ui';
import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ApiError } from '../../shared/api';
import { useConsentFlow } from '../../features/submission/use-consent-flow';
import { useConsentForm } from '../../features/token-validation/use-consent-form';

// Mirrors ConsentService._resolve_active_request's {"reason": ...} detail
// body on the backend — see apps/api/src/medical_api/modules/consents/
// service.py. Anything else (network failure, an unrecognized reason, a
// plain 500) falls back to the generic "unavailable" message rather than
// a misleading specific one.
const REASON_MESSAGES: Record<string, string> = {
  not_found:
    'Este enlace de consentimiento no existe. Verifica que copiaste la dirección completa.',
  expired: 'Este enlace ya expiró. Contacta a la clínica para que te envíen uno nuevo.',
  invalidated: 'Este enlace ya no está disponible. Contacta a la clínica para más información.',
  completed: 'Ya completaste este formulario de consentimiento. No es necesario hacerlo de nuevo.',
};
const UNAVAILABLE_MESSAGE =
  'No pudimos cargar tu formulario en este momento. Intenta de nuevo en unos minutos o contacta a la clínica.';

export function ConsentStartPage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const { setForm } = useConsentFlow();
  const { data, isLoading, isError, error } = useConsentForm(token);

  useEffect(() => {
    if (data) setForm(data);
  }, [data, setForm]);

  if (isLoading) return <StatusScreen message="Cargando tu formulario..." />;
  if (isError || !data) {
    const reason = error instanceof ApiError ? error.reason : undefined;
    const message = (reason && REASON_MESSAGES[reason]) || UNAVAILABLE_MESSAGE;
    return <StatusScreen message={message} isError />;
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-bold text-slate-900">Antes de tu cita</h1>
      <div
        className="prose prose-sm text-slate-700"
        dangerouslySetInnerHTML={{ __html: data.body_markdown }}
      />
      <p className="text-sm text-slate-500">
        Vas a responder unas preguntas breves y firmar con tu dedo. Esto toma menos de 3 minutos.
      </p>
      <Button
        type="button"
        size="lg"
        fullWidth
        onClick={() => navigate(`/c/${token}/questionnaire`)}
      >
        Comenzar
      </Button>
    </div>
  );
}

export function StatusScreen({ message, isError }: { message: string; isError?: boolean }) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 text-center">
      <p className={isError ? 'text-red-600' : 'text-slate-600'}>{message}</p>
    </div>
  );
}
