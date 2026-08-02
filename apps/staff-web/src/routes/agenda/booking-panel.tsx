import { Button, ErrorText, TextAreaField } from '@medical-platform/ui';
import { useState } from 'react';
import { useCreateAppointment } from '../../features/scheduling/use-create-appointment';
import type { AvailableSlot } from '../../features/scheduling/types';
import { usePatientSearch } from '../../features/patients/use-patients';
import type { Patient } from '../../features/patients/types';
import { formatTimeUTC } from './date-utils';

interface BookingPanelProps {
  practitionerId: string;
  slot: AvailableSlot;
  onClose: () => void;
  onBooked: () => void;
}

export function BookingPanel({ practitionerId, slot, onClose, onBooked }: BookingPanelProps) {
  const [query, setQuery] = useState('');
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [notes, setNotes] = useState('');
  const patientSearch = usePatientSearch(query);
  const createAppointment = useCreateAppointment();

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!selectedPatient) return;
    await createAppointment.mutateAsync({
      patient_id: selectedPatient.id,
      practitioner_id: practitionerId,
      starts_at: slot.starts_at,
      ends_at: slot.ends_at,
      notes: notes.trim() || undefined,
    });
    onBooked();
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="font-medium text-slate-900">
          Reservar {formatTimeUTC(slot.starts_at)}–{formatTimeUTC(slot.ends_at)}
        </h3>
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
              onClick={() => setSelectedPatient(null)}
              className="text-slate-500 underline"
            >
              Cambiar
            </button>
          </div>
        ) : (
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Paciente</label>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
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
            {patientSearch.data && patientSearch.data.length === 0 && query.trim().length >= 2 && (
              <p className="mt-2 text-sm text-slate-500">Sin resultados.</p>
            )}
          </div>
        )}
        <TextAreaField
          label="Notas (opcional)"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={2}
        />
        {createAppointment.isError && (
          <ErrorText>
            No se pudo crear la cita. Es posible que el horario ya no esté disponible.
          </ErrorText>
        )}
        <Button type="submit" disabled={!selectedPatient || createAppointment.isPending}>
          {createAppointment.isPending ? 'Reservando...' : 'Confirmar cita'}
        </Button>
      </form>
    </div>
  );
}
