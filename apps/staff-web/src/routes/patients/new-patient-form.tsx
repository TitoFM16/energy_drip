import { useState } from 'react';
import { useCreatePatient, type PatientInput } from '../../features/patients/use-create-patient';

interface NewPatientFormProps {
  onCreated: () => void;
}

const EMPTY: PatientInput = { first_name: '', last_name: '' };

export function NewPatientForm({ onCreated }: NewPatientFormProps) {
  const createPatient = useCreatePatient();
  const [form, setForm] = useState<PatientInput>(EMPTY);

  function field<K extends keyof PatientInput>(key: K) {
    return {
      value: form[key] ?? '',
      onChange: (e: React.ChangeEvent<HTMLInputElement>) =>
        setForm((f) => ({ ...f, [key]: e.target.value })),
    };
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const { first_name, last_name, document_id, date_of_birth, phone_number, email } = form;
    await createPatient.mutateAsync({
      first_name,
      last_name,
      document_id: document_id || undefined,
      date_of_birth: date_of_birth || undefined,
      phone_number: phone_number || undefined,
      email: email || undefined,
    });
    onCreated();
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mb-6 grid grid-cols-1 gap-3 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-2"
    >
      <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
        Nombre
        <input
          type="text"
          required
          {...field('first_name')}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
      </label>
      <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
        Apellido
        <input
          type="text"
          required
          {...field('last_name')}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
      </label>
      <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
        Documento
        <input
          type="text"
          {...field('document_id')}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
      </label>
      <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
        Fecha de nacimiento
        <input
          type="date"
          {...field('date_of_birth')}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
      </label>
      <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
        Teléfono
        <input
          type="tel"
          {...field('phone_number')}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
      </label>
      <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
        Correo electrónico
        <input
          type="email"
          {...field('email')}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
      </label>
      {createPatient.isError && (
        <p className="text-sm text-red-600 sm:col-span-2">No se pudo crear el paciente.</p>
      )}
      <button
        type="submit"
        disabled={createPatient.isPending}
        className="rounded-lg bg-slate-900 py-2.5 text-sm font-semibold text-white disabled:opacity-40 sm:col-span-2"
      >
        {createPatient.isPending ? 'Creando...' : 'Crear paciente'}
      </button>
    </form>
  );
}
