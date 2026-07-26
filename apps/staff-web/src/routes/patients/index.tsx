import { useQuery } from '@tanstack/react-query';
import { PageHeading } from '../../shared/components/app-shell';
import { apiFetch } from '../../shared/utilities/api';

interface Patient {
  id: string;
  first_name: string;
  last_name: string;
  phone_number: string | null;
}

export function PatientsPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['patients'],
    queryFn: () => apiFetch<Patient[]>('/api/v1/patients'),
  });

  return (
    <div>
      <PageHeading>Pacientes</PageHeading>
      {isLoading && <p className="text-slate-500">Cargando pacientes...</p>}
      {isError && <p className="text-red-600">No se pudo cargar la lista de pacientes.</p>}
      <div className="grid gap-3">
        {data?.map((patient) => (
          <div key={patient.id} className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="font-medium text-slate-900">
              {patient.first_name} {patient.last_name}
            </p>
            <p className="text-sm text-slate-500">
              {patient.phone_number ?? 'Sin teléfono registrado'}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
