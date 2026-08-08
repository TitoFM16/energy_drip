import { Button, ErrorText, TextField } from '@medical-platform/ui';
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { usePatient } from '../../features/patients/use-patient';
import { useUpdatePatient } from '../../features/patients/use-update-patient';
import { PageHeading } from '../../shared/components/app-shell';
import { CommunicationPreferencesSection } from './communication-preferences-section';
import { ConsentRequestsSection } from './consent-requests-section';
import { ContactsSection } from './contacts-section';
import { MedicalRecordSection } from './medical-record-section';
import { TreatmentPlansSection } from './treatment-plans-section';

export function PatientDetailPage() {
  const { patientId } = useParams<{ patientId: string }>();
  const { data: patient, isLoading, isError } = usePatient(patientId ?? '');
  const updatePatient = useUpdatePatient();

  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [documentId, setDocumentId] = useState('');
  const [dateOfBirth, setDateOfBirth] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');

  useEffect(() => {
    if (patient) {
      setFirstName(patient.first_name);
      setLastName(patient.last_name);
      setDocumentId(patient.document_id ?? '');
      setDateOfBirth(patient.date_of_birth ?? '');
      setPhone(patient.phone_number ?? '');
      setEmail(patient.email ?? '');
    }
  }, [patient]);

  if (!patientId) return null;
  if (isLoading) return <p className="text-slate-500">Cargando paciente...</p>;
  if (isError || !patient) return <ErrorText>No se pudo cargar el paciente.</ErrorText>;

  async function handleSave(event: React.FormEvent) {
    event.preventDefault();
    await updatePatient.mutateAsync({
      patientId: patient!.id,
      first_name: firstName,
      last_name: lastName,
      document_id: documentId || undefined,
      date_of_birth: dateOfBirth || undefined,
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

      <form
        onSubmit={handleSave}
        className="grid grid-cols-1 gap-3 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-2"
      >
        <TextField
          label="Nombre"
          type="text"
          required
          value={firstName}
          onChange={(e) => setFirstName(e.target.value)}
        />
        <TextField
          label="Apellido"
          type="text"
          required
          value={lastName}
          onChange={(e) => setLastName(e.target.value)}
        />
        <TextField
          label="Documento"
          type="text"
          value={documentId}
          onChange={(e) => setDocumentId(e.target.value)}
        />
        <TextField
          label="Fecha de nacimiento"
          type="date"
          value={dateOfBirth}
          onChange={(e) => setDateOfBirth(e.target.value)}
        />
        <TextField
          label="Teléfono"
          type="tel"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
        />
        <TextField
          label="Correo electrónico"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        {updatePatient.isError && (
          <ErrorText className="sm:col-span-2">No se pudieron guardar los cambios.</ErrorText>
        )}
        <div className="flex items-center gap-3 sm:col-span-2">
          <Button type="submit" disabled={updatePatient.isPending}>
            {updatePatient.isPending ? 'Guardando...' : 'Guardar cambios'}
          </Button>
          <Button
            type="button"
            variant="secondary"
            disabled={updatePatient.isPending}
            onClick={() =>
              updatePatient.mutate({ patientId: patient.id, is_active: !patient.is_active })
            }
          >
            {patient.is_active ? 'Marcar como inactivo' : 'Marcar como activo'}
          </Button>
        </div>
      </form>

      <CommunicationPreferencesSection patientId={patient.id} />
      <ContactsSection patientId={patient.id} />
      <MedicalRecordSection patientId={patient.id} />
      <TreatmentPlansSection patientId={patient.id} />
      <ConsentRequestsSection patientId={patient.id} />
    </div>
  );
}
