import { createContext, useMemo, useState, type ReactNode } from 'react';
import type { ConsentForm } from '../token-validation/use-consent-form';

export interface ConsentFlowState {
  form: ConsentForm | null;
  setForm: (form: ConsentForm) => void;
  answers: Record<string, unknown>;
  setAnswer: (fieldKey: string, value: unknown) => void;
  signatureSvg: string | null;
  setSignatureSvg: (svg: string) => void;
}

export const ConsentFlowContext = createContext<ConsentFlowState | null>(null);

export function ConsentFlowProvider({ children }: { children: ReactNode }) {
  const [form, setForm] = useState<ConsentForm | null>(null);
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [signatureSvg, setSignatureSvg] = useState<string | null>(null);

  const value = useMemo<ConsentFlowState>(
    () => ({
      form,
      setForm,
      answers,
      setAnswer: (fieldKey, fieldValue) =>
        setAnswers((prev) => ({ ...prev, [fieldKey]: fieldValue })),
      signatureSvg,
      setSignatureSvg,
    }),
    [form, answers, signatureSvg],
  );

  return <ConsentFlowContext.Provider value={value}>{children}</ConsentFlowContext.Provider>;
}
