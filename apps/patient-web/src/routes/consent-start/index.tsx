import { Button } from '@medical-platform/ui';
import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useConsentFlow } from '../../features/submission/use-consent-flow';
import { useConsentForm } from '../../features/token-validation/use-consent-form';

export function ConsentStartPage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const { setForm } = useConsentFlow();
  const { data, isLoading, isError } = useConsentForm(token);

  useEffect(() => {
    if (data) setForm(data);
  }, [data, setForm]);

  if (isLoading) return <StatusScreen message="Cargando tu formulario..." />;
  if (isError || !data) {
    return (
      <StatusScreen
        message="Este enlace no es válido o ya expiró. Contacta a la clínica para uno nuevo."
        isError
      />
    );
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
