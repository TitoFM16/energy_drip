import { Button, ErrorText } from '@medical-platform/ui';
import { useNavigate, useParams } from 'react-router-dom';
import { useConsentFlow } from '../../features/submission/use-consent-flow';
import { useSubmitConsent } from '../../features/submission/use-submit-consent';
import { StatusScreen } from '../consent-start';

export function ReviewPage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const { form, answers, signatureSvg } = useConsentFlow();
  const submitConsent = useSubmitConsent();

  if (!form || !signatureSvg) {
    return (
      <StatusScreen message="Falta información. Vuelve a empezar el flujo de consentimiento." />
    );
  }

  async function handleSubmit() {
    if (!token) return;
    const result = await submitConsent.mutateAsync({
      token,
      questions: form!.questions,
      answers,
      signatureSvg: signatureSvg!,
    });
    navigate(`/c/${token}/completed`, { state: { eligibilityResult: result.eligibility_result } });
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-bold text-slate-900">Revisa tus respuestas</h1>
      <ul className="flex flex-col gap-3">
        {form.questions.map((question) => (
          <li key={question.id} className="rounded-lg border border-slate-200 p-3">
            <p className="text-sm font-medium text-slate-800">{question.prompt}</p>
            <p className="text-sm text-slate-500">{String(answers[question.field_key] ?? '—')}</p>
          </li>
        ))}
      </ul>
      <div className="rounded-lg border border-slate-200 p-3">
        <p className="mb-2 text-sm font-medium text-slate-800">Tu firma</p>
        <div className="h-24 w-full" dangerouslySetInnerHTML={{ __html: signatureSvg }} />
      </div>
      {submitConsent.isError && <ErrorText>No se pudo enviar. Intenta de nuevo.</ErrorText>}
      <Button
        type="button"
        size="lg"
        fullWidth
        onClick={handleSubmit}
        disabled={submitConsent.isPending}
      >
        {submitConsent.isPending ? 'Enviando...' : 'Enviar consentimiento'}
      </Button>
    </div>
  );
}
