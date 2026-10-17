import { SimplePage } from '../components/page-layout';

export function TerminosPage() {
  return (
    <SimplePage title="Condiciones de la reserva">
      <article>
        <h2>Confirmación de la cita</h2>
        <p>
          La reserva queda registrada cuando aparece la confirmación con su referencia. El servicio,
          el profesional, la fecha y la hora se muestran antes de confirmar. Todos los horarios
          corresponden a Colombia (UTC−5).
        </p>
      </article>
      <article>
        <h2>Servicios y precios</h2>
        <p>
          El catálogo muestra el precio y la duración de cada servicio. Esta aplicación registra
          citas y no procesa pagos. Cualquier condición de pago se coordina directamente con el
          equipo.
        </p>
      </article>
      <article>
        <h2>Cambios y cancelaciones</h2>
        <p>
          Para solicitar un cambio o cancelar, contacta al equipo de Energy Drip e indica tu
          referencia de reserva. El equipo confirmará el nuevo horario según la disponibilidad.
        </p>
      </article>
      <article>
        <h2>Atención profesional</h2>
        <p>
          Reservar un horario no sustituye una valoración profesional. Cuando corresponda, el equipo
          explicará el servicio y solicitará el consentimiento informado antes de realizarlo.
        </p>
      </article>
    </SimplePage>
  );
}
