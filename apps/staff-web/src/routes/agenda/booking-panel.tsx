import { Button, ErrorText, TextAreaField, TextField } from '@medical-platform/ui';
import { useState } from 'react';
import { useCreateAppointment } from '../../features/scheduling/use-create-appointment';
import type { AvailableSlot } from '../../features/scheduling/types';
import { usePatientSearch } from '../../features/patients/use-patients';
import { useCreatePatient } from '../../features/patients/use-create-patient';
import type { Patient } from '../../features/patients/types';
import type { TreatmentDefinition } from '../../features/treatments/types';
import { formatTimeClinic } from './date-utils';

interface BookingPanelProps {
  practitionerId: string;
  service: TreatmentDefinition;
  slot: AvailableSlot;
  onClose: () => void;
  onBooked: () => void;
}
export function BookingPanel({
  practitionerId,
  service,
  slot,
  onClose,
  onBooked,
}: BookingPanelProps) {
  const [query, setQuery] = useState('');
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [newPatient, setNewPatient] = useState(false);
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [phone, setPhone] = useState('');
  const [notes, setNotes] = useState('');
  const patientSearch = usePatientSearch(query);
  const createPatient = useCreatePatient();
  const createAppointment = useCreateAppointment();
  const busy = createPatient.isPending || createAppointment.isPending;
  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    try {
      let patient = selectedPatient;
      if (!patient && newPatient) {
        patient = await createPatient.mutateAsync({
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          phone_number: phone.trim(),
        });
        setSelectedPatient(patient);
      }
      if (!patient) return;
      await createAppointment.mutateAsync({
        patient_id: patient.id,
        practitioner_id: practitionerId,
        treatment_definition_id: service.id,
        starts_at: slot.starts_at,
        ends_at: slot.ends_at,
        notes: notes.trim() || undefined,
      });
      onBooked();
    } catch {
      /* Errors are shown in the panel and the patient remains selected for retry. */
    }
  }
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h3 className="font-medium">
            Reservar {formatTimeClinic(slot.starts_at)}–{formatTimeClinic(slot.ends_at)}
          </h3>
          <p className="text-sm text-slate-500">
            {service.name} · {service.duration_minutes} min
          </p>
        </div>
        <button type="button" onClick={onClose} className="text-sm text-slate-500 underline">
          Cancelar
        </button>
      </div>
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        {selectedPatient ? (
          <div className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-sm">
            <span>
              {selectedPatient.first_name} {selectedPatient.last_name}
            </span>
            <button
              type="button"
              onClick={() => {
                setSelectedPatient(null);
                setNewPatient(false);
              }}
              className="underline"
            >
              Cambiar
            </button>
          </div>
        ) : (
          <>
            <div className="flex gap-4 text-sm">
              <button
                type="button"
                aria-pressed={!newPatient}
                onClick={() => setNewPatient(false)}
                className="underline"
              >
                Paciente existente
              </button>
              <button
                type="button"
                aria-pressed={newPatient}
                onClick={() => setNewPatient(true)}
                className="underline"
              >
                Nuevo paciente
              </button>
            </div>
            {newPatient ? (
              <>
                <TextField
                  label="Nombre del paciente"
                  required
                  maxLength={150}
                  value={firstName}
                  onChange={(event) => setFirstName(event.target.value)}
                />
                <TextField
                  label="Apellido del paciente"
                  required
                  maxLength={150}
                  value={lastName}
                  onChange={(event) => setLastName(event.target.value)}
                />
                <TextField
                  label="Teléfono del paciente"
                  type="tel"
                  required
                  maxLength={30}
                  value={phone}
                  onChange={(event) => setPhone(event.target.value)}
                />
              </>
            ) : (
              <div>
                <label
                  htmlFor="patient-search"
                  className="mb-1 block text-sm font-medium text-slate-700"
                >
                  Paciente
                </label>
                <input
                  id="patient-search"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Buscar por nombre..."
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
                {patientSearch.data && patientSearch.data.length > 0 && (
                  <ul className="mt-2 divide-y divide-slate-100 rounded-lg border border-slate-200">
                    {patientSearch.data.map((patient) => (
                      <li key={patient.id}>
                        <button
                          type="button"
                          onClick={() => setSelectedPatient(patient)}
                          className="w-full px-3 py-2 text-left text-sm hover:bg-slate-50"
                        >
                          {patient.first_name} {patient.last_name}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
                {patientSearch.data?.length === 0 && query.trim().length >= 2 && (
                  <p className="mt-2 text-sm text-slate-500">
                    Sin resultados. Puedes agregar un nuevo paciente.
                  </p>
                )}
                {patientSearch.isError && <ErrorText>No se pudo buscar al paciente.</ErrorText>}
              </div>
            )}
          </>
        )}
        <TextAreaField
          label="Notas (opcional)"
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          rows={2}
        />
        {createPatient.isError && (
          <ErrorText>No se pudo guardar el paciente. Revisa sus datos.</ErrorText>
        )}
        {createAppointment.isError && (
          <ErrorText>
            No se pudo crear la cita. El horario puede haberse ocupado; cierra este panel y elige
            otro.
          </ErrorText>
        )}
        <Button type="submit" disabled={(!selectedPatient && !newPatient) || busy}>
          {busy ? 'Reservando…' : 'Confirmar cita'}
        </Button>
      </form>
    </div>
  );
}
