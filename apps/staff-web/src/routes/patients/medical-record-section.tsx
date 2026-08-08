import { Badge, Button, ErrorText, TextField } from '@medical-platform/ui';
import { useState } from 'react';
import {
  useAllergies,
  useCreateAllergy,
  useUpdateAllergy,
} from '../../features/patient-record/use-allergies';
import {
  useConditions,
  useCreateCondition,
  useUpdateCondition,
} from '../../features/patient-record/use-conditions';
import {
  useCreateMedicalHistoryEntry,
  useFinalizeMedicalHistoryEntry,
  useMedicalHistory,
} from '../../features/patient-record/use-medical-history';
import {
  useCreateMedication,
  useMedications,
  useUpdateMedication,
} from '../../features/patient-record/use-medications';

interface PatientRecordSectionProps {
  patientId: string;
}

export function MedicalRecordSection({ patientId }: PatientRecordSectionProps) {
  return (
    <section className="mt-6">
      <h2 className="mb-3 text-sm font-semibold tracking-wide text-slate-500 uppercase">
        Historial clínico
      </h2>
      <div className="flex flex-col gap-4">
        <MedicalHistorySubsection patientId={patientId} />
        <AllergiesSubsection patientId={patientId} />
        <ConditionsSubsection patientId={patientId} />
        <MedicationsSubsection patientId={patientId} />
      </div>
    </section>
  );
}

function MedicalHistorySubsection({ patientId }: PatientRecordSectionProps) {
  const history = useMedicalHistory(patientId);
  const createEntry = useCreateMedicalHistoryEntry();
  const finalizeEntry = useFinalizeMedicalHistoryEntry();
  const [summary, setSummary] = useState('');
  const [amendingId, setAmendingId] = useState<string | null>(null);
  const [correctionText, setCorrectionText] = useState('');

  async function handleAdd(event: React.FormEvent) {
    event.preventDefault();
    if (!summary.trim()) return;
    await createEntry.mutateAsync({ patient_id: patientId, summary: summary.trim() });
    setSummary('');
  }

  async function handleCorrect(entryId: string) {
    if (!correctionText.trim()) return;
    await createEntry.mutateAsync({
      patient_id: patientId,
      summary: correctionText.trim(),
      amends_entry_id: entryId,
    });
    setCorrectionText('');
    setAmendingId(null);
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="mb-2 text-sm font-medium text-slate-700">Antecedentes</h3>
      <ul className="mb-3 flex flex-col gap-2">
        {history.data?.map((entry) => (
          <li key={entry.id} className="rounded-lg bg-slate-50 px-3 py-2 text-sm">
            <div className="flex items-center justify-between gap-2">
              <p className="text-slate-800">{entry.summary}</p>
              <Badge>{entry.is_finalized ? 'Finalizado' : 'Borrador'}</Badge>
            </div>
            <div className="mt-1 flex gap-2">
              {!entry.is_finalized && (
                <button
                  type="button"
                  disabled={finalizeEntry.isPending}
                  onClick={() => finalizeEntry.mutate(entry.id)}
                  className="text-xs text-slate-500 underline disabled:opacity-40"
                >
                  Finalizar
                </button>
              )}
              {entry.is_finalized && amendingId !== entry.id && (
                <button
                  type="button"
                  onClick={() => setAmendingId(entry.id)}
                  className="text-xs text-slate-500 underline"
                >
                  Corregir
                </button>
              )}
            </div>
            {amendingId === entry.id && (
              <div className="mt-2 flex flex-wrap items-end gap-2">
                <input
                  type="text"
                  value={correctionText}
                  onChange={(e) => setCorrectionText(e.target.value)}
                  placeholder="Texto de la corrección"
                  className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
                />
                <Button
                  type="button"
                  size="sm"
                  disabled={createEntry.isPending}
                  onClick={() => handleCorrect(entry.id)}
                >
                  Guardar corrección
                </Button>
              </div>
            )}
          </li>
        ))}
        {history.data?.length === 0 && (
          <p className="text-sm text-slate-500">Sin antecedentes registrados todavía.</p>
        )}
      </ul>
      <form onSubmit={handleAdd} className="flex flex-wrap items-end gap-2">
        <TextField
          label="Nuevo antecedente"
          type="text"
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
        />
        <Button type="submit" size="sm" disabled={!summary.trim() || createEntry.isPending}>
          {createEntry.isPending ? 'Guardando...' : 'Agregar'}
        </Button>
      </form>
      {createEntry.isError && <ErrorText className="mt-2">No se pudo guardar.</ErrorText>}
    </div>
  );
}

function AllergiesSubsection({ patientId }: PatientRecordSectionProps) {
  const allergies = useAllergies(patientId);
  const createAllergy = useCreateAllergy();
  const updateAllergy = useUpdateAllergy();
  const [substance, setSubstance] = useState('');
  const [severity, setSeverity] = useState('');

  async function handleAdd(event: React.FormEvent) {
    event.preventDefault();
    if (!substance.trim()) return;
    await createAllergy.mutateAsync({
      patient_id: patientId,
      substance: substance.trim(),
      severity: severity.trim() || undefined,
    });
    setSubstance('');
    setSeverity('');
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="mb-2 text-sm font-medium text-slate-700">Alergias</h3>
      <ul className="mb-3 flex flex-col gap-2">
        {allergies.data?.map((allergy) => (
          <li
            key={allergy.id}
            className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm"
          >
            <span className={allergy.is_active ? 'text-slate-800' : 'text-slate-400 line-through'}>
              {allergy.substance}
              {allergy.severity ? ` · ${allergy.severity}` : ''}
            </span>
            <button
              type="button"
              disabled={updateAllergy.isPending}
              onClick={() =>
                updateAllergy.mutate({ allergyId: allergy.id, is_active: !allergy.is_active })
              }
              className="text-xs text-slate-500 underline disabled:opacity-40"
            >
              {allergy.is_active ? 'Desactivar' : 'Reactivar'}
            </button>
          </li>
        ))}
        {allergies.data?.length === 0 && (
          <p className="text-sm text-slate-500">Sin alergias registradas.</p>
        )}
      </ul>
      <form onSubmit={handleAdd} className="flex flex-wrap items-end gap-2">
        <TextField
          label="Sustancia"
          type="text"
          value={substance}
          onChange={(e) => setSubstance(e.target.value)}
        />
        <TextField
          label="Severidad"
          type="text"
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
        />
        <Button type="submit" size="sm" disabled={!substance.trim() || createAllergy.isPending}>
          {createAllergy.isPending ? 'Guardando...' : 'Agregar'}
        </Button>
      </form>
      {createAllergy.isError && <ErrorText className="mt-2">No se pudo guardar.</ErrorText>}
    </div>
  );
}

function ConditionsSubsection({ patientId }: PatientRecordSectionProps) {
  const conditions = useConditions(patientId);
  const createCondition = useCreateCondition();
  const updateCondition = useUpdateCondition();
  const [name, setName] = useState('');

  async function handleAdd(event: React.FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    await createCondition.mutateAsync({ patient_id: patientId, name: name.trim() });
    setName('');
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="mb-2 text-sm font-medium text-slate-700">Condiciones</h3>
      <ul className="mb-3 flex flex-col gap-2">
        {conditions.data?.map((condition) => (
          <li
            key={condition.id}
            className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm"
          >
            <span
              className={condition.is_active ? 'text-slate-800' : 'text-slate-400 line-through'}
            >
              {condition.name}
            </span>
            <button
              type="button"
              disabled={updateCondition.isPending}
              onClick={() =>
                updateCondition.mutate({
                  conditionId: condition.id,
                  is_active: !condition.is_active,
                })
              }
              className="text-xs text-slate-500 underline disabled:opacity-40"
            >
              {condition.is_active ? 'Desactivar' : 'Reactivar'}
            </button>
          </li>
        ))}
        {conditions.data?.length === 0 && (
          <p className="text-sm text-slate-500">Sin condiciones registradas.</p>
        )}
      </ul>
      <form onSubmit={handleAdd} className="flex flex-wrap items-end gap-2">
        <TextField
          label="Condición"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <Button type="submit" size="sm" disabled={!name.trim() || createCondition.isPending}>
          {createCondition.isPending ? 'Guardando...' : 'Agregar'}
        </Button>
      </form>
      {createCondition.isError && <ErrorText className="mt-2">No se pudo guardar.</ErrorText>}
    </div>
  );
}

function MedicationsSubsection({ patientId }: PatientRecordSectionProps) {
  const medications = useMedications(patientId);
  const createMedication = useCreateMedication();
  const updateMedication = useUpdateMedication();
  const [name, setName] = useState('');
  const [dosage, setDosage] = useState('');

  async function handleAdd(event: React.FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    await createMedication.mutateAsync({
      patient_id: patientId,
      name: name.trim(),
      dosage: dosage.trim() || undefined,
    });
    setName('');
    setDosage('');
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="mb-2 text-sm font-medium text-slate-700">Medicamentos</h3>
      <ul className="mb-3 flex flex-col gap-2">
        {medications.data?.map((medication) => (
          <li
            key={medication.id}
            className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm"
          >
            <span
              className={medication.is_current ? 'text-slate-800' : 'text-slate-400 line-through'}
            >
              {medication.name}
              {medication.dosage ? ` · ${medication.dosage}` : ''}
            </span>
            <button
              type="button"
              disabled={updateMedication.isPending}
              onClick={() =>
                updateMedication.mutate({
                  medicationId: medication.id,
                  is_current: !medication.is_current,
                })
              }
              className="text-xs text-slate-500 underline disabled:opacity-40"
            >
              {medication.is_current ? 'Suspender' : 'Reanudar'}
            </button>
          </li>
        ))}
        {medications.data?.length === 0 && (
          <p className="text-sm text-slate-500">Sin medicamentos registrados.</p>
        )}
      </ul>
      <form onSubmit={handleAdd} className="flex flex-wrap items-end gap-2">
        <TextField
          label="Medicamento"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <TextField
          label="Dosis"
          type="text"
          value={dosage}
          onChange={(e) => setDosage(e.target.value)}
        />
        <Button type="submit" size="sm" disabled={!name.trim() || createMedication.isPending}>
          {createMedication.isPending ? 'Guardando...' : 'Agregar'}
        </Button>
      </form>
      {createMedication.isError && <ErrorText className="mt-2">No se pudo guardar.</ErrorText>}
    </div>
  );
}
