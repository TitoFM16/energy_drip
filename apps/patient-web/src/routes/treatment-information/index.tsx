import { useNavigate, useParams } from 'react-router-dom';
import { useConsentFlow } from '../../features/submission/use-consent-flow';
import { StatusScreen } from '../consent-start';

export function TreatmentInformationPage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const { form } = useConsentFlow();

  if (!form) {
    return <StatusScreen message="Carga el enlace de consentimiento desde el inicio." />;
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-bold text-slate-900">Consentimiento informado</h1>
      <div
        className="prose prose-sm text-slate-700"
        dangerouslySetInnerHTML={{ __html: form.body_markdown }}
      />
      <p className="text-sm text-slate-500">
        Al continuar y firmar, confirmas que leíste esta información y respondiste el cuestionario
        con la verdad.
      </p>
      <button
        type="button"
        onClick={() => navigate(`/c/${token}/signature`)}
        className="rounded-lg bg-slate-900 py-4 text-base font-semibold text-white"
      >
        Ir a firmar
      </button>
    </div>
  );
}
