import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { usePatient } from '../../features/patients/use-patient';
import { useUpdatePatient } from '../../features/patients/use-update-patient';
import { PageHeading } from '../../shared/components/app-shell';
import { TreatmentPlansSection } from './treatment-plans-section';

export function PatientDetailPage() {
  const { patientId } = useParams<{ patientId: string }>();
  const { data: patient, isLoading, isError } = usePatient(patientId ?? '');
  const updatePatient = useUpdatePatient();

  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');

  useEffect(() => {
    if (patient) {
      setFirstName(patient.first_name);
      setLastName(patient.last_name);
      setPhone(patient.phone_number ?? '');
      setEmail(patient.email ?? '');
    }
  }, [patient]);

  if (!patientId) return null;
  if (isLoading) return <p className="text-slate-500">Cargando paciente...</p>;
  if (isError || !patient) return <p className="text-red-600">No se pudo cargar el paciente.</p>;

  async function handleSave(event: React.FormEvent) {
    event.preventDefault();
    await updatePatient.mutateAsync({
      patientId: patient!.id,
      first_name: firstName,
      last_name: lastName,
      phone_number: phone || undefined,
      email: email || undefined,
    });
  }

  return (
    <div>
      <Link to="/patients" className="mb-4 inline-block text-sm text-slate-500 underline">
        ← Volver a pacientes
      </Link>
      <PageHeading>
        {patient.first_name} {patient.last_name}
      </PageHeading>

      <div className="mb-6 grid grid-cols-1 gap-3 rounded-lg border border-slate-200 bg-white p-4 text-sm sm:grid-cols-2">
        <div>
          <p className="text-slate-500">Documento</p>
          <p className="text-slate-900">{patient.document_id ?? '—'}</p>
        </div>
        <div>
          <p className="text-slate-500">Fecha de nacimiento</p>
          <p className="text-slate-900">{patient.date_of_birth ?? '—'}</p>
        </div>
      </div>

      <form
        onSubmit={handleSave}
        className="grid grid-cols-1 gap-3 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-2"
      >
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
          Nombre
          <input
            type="text"
            required
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
          Apellido
          <input
            type="text"
            required
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
          Teléfono
          <input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
          Correo electrónico
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </label>
        {updatePatient.isError && (
          <p className="text-sm text-red-600 sm:col-span-2">No se pudieron guardar los cambios.</p>
        )}
        <div className="flex items-center gap-3 sm:col-span-2">
          <button
            type="submit"
            disabled={updatePatient.isPending}
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
          >
            {updatePatient.isPending ? 'Guardando...' : 'Guardar cambios'}
          </button>
          <button
            type="button"
            disabled={updatePatient.isPending}
            onClick={() =>
              updatePatient.mutate({ patientId: patient.id, is_active: !patient.is_active })
            }
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-40"
          >
            {patient.is_active ? 'Marcar como inactivo' : 'Marcar como activo'}
          </button>
        </div>
      </form>

      <TreatmentPlansSection patientId={patient.id} />
    </div>
  );
}
