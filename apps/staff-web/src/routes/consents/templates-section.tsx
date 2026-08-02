import { useState } from 'react';
import {
  useConsentTemplates,
  useCreateConsentTemplate,
  usePublishConsentTemplateVersion,
} from '../../features/consents/use-consent-templates';
import type { ConsentQuestionInput, QuestionType } from '../../features/consents/types';

const QUESTION_TYPE_LABELS: Record<QuestionType, string> = {
  boolean: 'Sí / No',
  single_choice: 'Opción única',
  multiple_choice: 'Opción múltiple',
  text: 'Texto libre',
  number: 'Número',
};

function emptyQuestion(order: number): ConsentQuestionInput {
  return {
    field_key: '',
    prompt: '',
    question_type: 'boolean',
    display_order: order,
    is_required: true,
    options: [],
  };
}

export function TemplatesSection() {
  const templates = useConsentTemplates();
  const createTemplate = useCreateConsentTemplate();
  const publishVersion = usePublishConsentTemplateVersion();

  const [name, setName] = useState('');
  const [bodyMarkdown, setBodyMarkdown] = useState('');
  const [questions, setQuestions] = useState<ConsentQuestionInput[]>([emptyQuestion(0)]);

  function updateQuestion(index: number, patch: Partial<ConsentQuestionInput>) {
    setQuestions((qs) => qs.map((q, i) => (i === index ? { ...q, ...patch } : q)));
  }

  function addQuestion() {
    setQuestions((qs) => [...qs, emptyQuestion(qs.length)]);
  }

  function removeQuestion(index: number) {
    setQuestions((qs) => qs.filter((_, i) => i !== index));
  }

  function addOption(index: number) {
    updateQuestion(index, {
      options: [...questions[index].options, { value: '', label: '' }],
    });
  }

  function updateOption(qIndex: number, oIndex: number, patch: { value?: string; label?: string }) {
    const options = questions[qIndex].options.map((o, i) =>
      i === oIndex ? { ...o, ...patch } : o,
    );
    updateQuestion(qIndex, { options });
  }

  function removeOption(qIndex: number, oIndex: number) {
    updateQuestion(qIndex, { options: questions[qIndex].options.filter((_, i) => i !== oIndex) });
  }

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    await createTemplate.mutateAsync({
      name,
      body_markdown: bodyMarkdown,
      questions: questions.filter((q) => q.field_key && q.prompt),
    });
    setName('');
    setBodyMarkdown('');
    setQuestions([emptyQuestion(0)]);
  }

  return (
    <section>
      <h2 className="mb-3 text-sm font-semibold tracking-wide text-slate-500 uppercase">
        Plantillas de consentimiento
      </h2>

      {templates.isLoading && <p className="text-slate-500">Cargando plantillas...</p>}
      {templates.isError && <p className="text-red-600">No se pudieron cargar las plantillas.</p>}
      {templates.data && templates.data.length === 0 && (
        <p className="mb-4 text-slate-500">Todavía no hay plantillas.</p>
      )}

      <ul className="mb-6 divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
        {templates.data?.map((template) => (
          <li key={template.id} className="flex items-center justify-between gap-3 px-4 py-3">
            <div>
              <p className="text-sm font-medium text-slate-900">{template.name}</p>
              <p className="text-xs text-slate-500">
                {template.latest_version
                  ? `Versión ${template.latest_version.version_number}`
                  : 'Sin versión'}
              </p>
            </div>
            {template.latest_version &&
              (template.latest_version.published_at ? (
                <span className="rounded-full bg-green-50 px-2.5 py-1 text-xs font-medium text-green-700">
                  Publicada
                </span>
              ) : (
                <button
                  type="button"
                  disabled={publishVersion.isPending}
                  onClick={() =>
                    publishVersion.mutate({
                      templateId: template.id,
                      versionId: template.latest_version!.id,
                    })
                  }
                  className="rounded-full border border-slate-300 px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-50 disabled:opacity-40"
                >
                  Borrador — publicar
                </button>
              ))}
          </li>
        ))}
      </ul>

      <form
        onSubmit={handleCreate}
        className="flex flex-col gap-4 rounded-lg border border-slate-200 bg-white p-4"
      >
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
          Nombre de la plantilla
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
          Texto del consentimiento
          <textarea
            required
            rows={4}
            value={bodyMarkdown}
            onChange={(e) => setBodyMarkdown(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </label>

        <div className="flex flex-col gap-3">
          <p className="text-sm font-medium text-slate-700">Preguntas</p>
          {questions.map((question, qIndex) => (
            <div key={qIndex} className="rounded-lg border border-slate-200 p-3">
              <div className="mb-2 flex flex-wrap items-end gap-2">
                <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
                  Clave
                  <input
                    type="text"
                    value={question.field_key}
                    onChange={(e) => updateQuestion(qIndex, { field_key: e.target.value })}
                    className="w-32 rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
                  />
                </label>
                <label className="flex flex-1 flex-col gap-1 text-xs font-medium text-slate-600">
                  Pregunta
                  <input
                    type="text"
                    value={question.prompt}
                    onChange={(e) => updateQuestion(qIndex, { prompt: e.target.value })}
                    className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
                  />
                </label>
                <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
                  Tipo
                  <select
                    value={question.question_type}
                    onChange={(e) =>
                      updateQuestion(qIndex, { question_type: e.target.value as QuestionType })
                    }
                    className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
                  >
                    {Object.entries(QUESTION_TYPE_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex items-center gap-1 text-xs font-medium text-slate-600">
                  <input
                    type="checkbox"
                    checked={question.is_required}
                    onChange={(e) => updateQuestion(qIndex, { is_required: e.target.checked })}
                  />
                  Obligatoria
                </label>
                <button
                  type="button"
                  onClick={() => removeQuestion(qIndex)}
                  className="text-xs text-red-600 underline"
                >
                  Quitar
                </button>
              </div>

              {(question.question_type === 'single_choice' ||
                question.question_type === 'multiple_choice') && (
                <div className="ml-4 flex flex-col gap-2">
                  {question.options.map((option, oIndex) => (
                    <div key={oIndex} className="flex items-center gap-2">
                      <input
                        type="text"
                        placeholder="valor"
                        value={option.value}
                        onChange={(e) => updateOption(qIndex, oIndex, { value: e.target.value })}
                        className="w-28 rounded-lg border border-slate-300 px-2 py-1 text-xs"
                      />
                      <input
                        type="text"
                        placeholder="etiqueta"
                        value={option.label}
                        onChange={(e) => updateOption(qIndex, oIndex, { label: e.target.value })}
                        className="w-40 rounded-lg border border-slate-300 px-2 py-1 text-xs"
                      />
                      <button
                        type="button"
                        onClick={() => removeOption(qIndex, oIndex)}
                        className="text-xs text-red-600 underline"
                      >
                        Quitar
                      </button>
                    </div>
                  ))}
                  <button
                    type="button"
                    onClick={() => addOption(qIndex)}
                    className="w-fit text-xs text-slate-600 underline"
                  >
                    + Agregar opción
                  </button>
                </div>
              )}
            </div>
          ))}
          <button
            type="button"
            onClick={addQuestion}
            className="w-fit rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
          >
            + Agregar pregunta
          </button>
        </div>

        {createTemplate.isError && (
          <p className="text-sm text-red-600">No se pudo crear la plantilla.</p>
        )}
        <button
          type="submit"
          disabled={createTemplate.isPending}
          className="w-fit rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
        >
          {createTemplate.isPending ? 'Creando...' : 'Crear plantilla'}
        </button>
      </form>
    </section>
  );
}
