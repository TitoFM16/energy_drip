import { Button, ErrorText, TextField } from '@medical-platform/ui';
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
      <TextField label="Nombre" type="text" required {...field('first_name')} />
      <TextField label="Apellido" type="text" required {...field('last_name')} />
      <TextField label="Documento" type="text" {...field('document_id')} />
      <TextField label="Fecha de nacimiento" type="date" {...field('date_of_birth')} />
      <TextField label="Teléfono" type="tel" {...field('phone_number')} />
      <TextField label="Correo electrónico" type="email" {...field('email')} />
      {createPatient.isError && (
        <ErrorText className="sm:col-span-2">No se pudo crear el paciente.</ErrorText>
      )}
      <Button type="submit" disabled={createPatient.isPending} className="sm:col-span-2">
        {createPatient.isPending ? 'Creando...' : 'Crear paciente'}
      </Button>
    </form>
  );
}
