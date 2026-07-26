import type { ConsentQuestion } from '../token-validation/use-consent-form';

interface DynamicFormProps {
  questions: ConsentQuestion[];
  answers: Record<string, unknown>;
  onChange: (fieldKey: string, value: unknown) => void;
}

/**
 * Renders whatever question set the backend returns for the active
 * template version — the medical filter is data, not hard-coded React,
 * so new questions/rules ship without a frontend deploy.
 */
export function DynamicForm({ questions, answers, onChange }: DynamicFormProps) {
  return (
    <div className="flex flex-col gap-5">
      {questions
        .slice()
        .sort((a, b) => a.display_order - b.display_order)
        .map((question) => (
          <QuestionField
            key={question.id}
            question={question}
            value={answers[question.field_key]}
            onChange={(value) => onChange(question.field_key, value)}
          />
        ))}
    </div>
  );
}

function QuestionField({
  question,
  value,
  onChange,
}: {
  question: ConsentQuestion;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  return (
    <label className="flex flex-col gap-2 text-sm font-medium text-slate-800">
      {question.prompt}
      {question.question_type === 'boolean' && (
        <div className="flex gap-3">
          {[
            { label: 'Sí', val: true },
            { label: 'No', val: false },
          ].map((option) => (
            <button
              key={option.label}
              type="button"
              onClick={() => onChange(option.val)}
              className={`flex-1 rounded-lg border px-4 py-3 text-base font-semibold ${
                value === option.val
                  ? 'border-slate-900 bg-slate-900 text-white'
                  : 'border-slate-300 bg-white text-slate-700'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      )}
      {question.question_type === 'single_choice' && (
        <select
          className="rounded-lg border border-slate-300 px-3 py-3 text-base"
          value={(value as string) ?? ''}
          onChange={(event) => onChange(event.target.value)}
        >
          <option value="" disabled>
            Selecciona una opción
          </option>
          {question.options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      )}
      {question.question_type === 'multiple_choice' && (
        <div className="flex flex-col gap-2">
          {question.options.map((option) => {
            const selected = Array.isArray(value) ? (value as string[]) : [];
            const checked = selected.includes(option.value);
            return (
              <label
                key={option.value}
                className="flex items-center gap-2 text-base font-normal text-slate-700"
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(event) =>
                    onChange(
                      event.target.checked
                        ? [...selected, option.value]
                        : selected.filter((v) => v !== option.value),
                    )
                  }
                />
                {option.label}
              </label>
            );
          })}
        </div>
      )}
      {(question.question_type === 'text' || question.question_type === 'number') && (
        <input
          type={question.question_type === 'number' ? 'number' : 'text'}
          className="rounded-lg border border-slate-300 px-3 py-3 text-base"
          value={(value as string) ?? ''}
          onChange={(event) =>
            onChange(
              question.question_type === 'number' ? Number(event.target.value) : event.target.value,
            )
          }
        />
      )}
    </label>
  );
}
