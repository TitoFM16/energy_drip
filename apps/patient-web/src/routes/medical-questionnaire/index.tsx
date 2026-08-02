import { Button } from '@medical-platform/ui';
import { useNavigate, useParams } from 'react-router-dom';
import { DynamicForm } from '../../features/dynamic-form/dynamic-form';
import { hasIncompleteRequiredAnswers } from '../../features/dynamic-form/validation';
import { useConsentFlow } from '../../features/submission/use-consent-flow';
import { StatusScreen } from '../consent-start';

export function MedicalQuestionnairePage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const { form, answers, setAnswer } = useConsentFlow();

  if (!form) {
    return <StatusScreen message="Carga el enlace de consentimiento desde el inicio." />;
  }

  const requiredMissing = hasIncompleteRequiredAnswers(form.questions, answers);

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-bold text-slate-900">Filtro médico</h1>
      <DynamicForm questions={form.questions} answers={answers} onChange={setAnswer} />
      <Button
        type="button"
        size="lg"
        fullWidth
        disabled={requiredMissing}
        onClick={() => navigate(`/c/${token}/treatment-information`)}
      >
        Continuar
      </Button>
    </div>
  );
}
