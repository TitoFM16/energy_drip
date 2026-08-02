import { useState } from 'react';
import { Link } from 'react-router-dom';
import { usePatients, usePatientSearch } from '../../features/patients/use-patients';
import { PageHeading } from '../../shared/components/app-shell';
import { NewPatientForm } from './new-patient-form';

export function PatientsPage() {
  const [query, setQuery] = useState('');
  const [showForm, setShowForm] = useState(false);
  const allPatients = usePatients();
  const searchResults = usePatientSearch(query);
  const isSearching = query.trim().length >= 2;
  const { data, isLoading, isError } = isSearching ? searchResults : allPatients;

  return (
    <div>
      <PageHeading>Pacientes</PageHeading>

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Buscar por nombre..."
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
        <button
          type="button"
          onClick={() => setShowForm((v) => !v)}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white"
        >
          {showForm ? 'Cancelar' : 'Nuevo paciente'}
        </button>
      </div>

      {showForm && <NewPatientForm onCreated={() => setShowForm(false)} />}

      {isLoading && <p className="text-slate-500">Cargando pacientes...</p>}
      {isError && <p className="text-red-600">No se pudo cargar la lista de pacientes.</p>}
      {data && data.length === 0 && (
        <p className="text-slate-500">
          {isSearching ? 'Sin resultados para esa búsqueda.' : 'Todavía no hay pacientes.'}
        </p>
      )}

      <div className="grid gap-3">
        {data?.map((patient) => (
          <Link
            key={patient.id}
            to={`/patients/${patient.id}`}
            className="rounded-lg border border-slate-200 bg-white p-4 hover:border-slate-400"
          >
            <div className="flex items-center justify-between">
              <p className="font-medium text-slate-900">
                {patient.first_name} {patient.last_name}
              </p>
              {!patient.is_active && (
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500">
                  Inactivo
                </span>
              )}
            </div>
            <p className="text-sm text-slate-500">
              {patient.phone_number ?? 'Sin teléfono registrado'}
            </p>
          </Link>
        ))}
      </div>
    </div>
  );
}
