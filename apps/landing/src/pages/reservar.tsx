import { SimplePage } from '../components/page-layout';

export function ReservarPage() {
  return (
    <SimplePage title="Reservar cita">
      <p>
        El flujo de reserva pública se conecta al mismo backend que usa el equipo de la clínica
        (`POST /api/v1/appointments`). Aquí vive el formulario de reserva para pacientes nuevos.
      </p>
    </SimplePage>
  );
}
