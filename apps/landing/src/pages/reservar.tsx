import { useEffect, useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { SimplePage } from '../components/page-layout';
import {
  formatAppointment,
  formatPrice,
  localDate,
  useCatalogue,
  type AvailableSlot,
  type PublicPractitioner,
} from '../features/booking/catalogue';
import { apiFetch, ApiError } from '../shared/api';

interface Confirmation {
  id: string;
  starts_at: string;
  ends_at: string;
  treatment_name: string;
  practitioner_name: string;
  detail: string;
}
const EMPTY_CONTACT = {
  first_name: '',
  last_name: '',
  phone_number: '',
  email: '',
  message: '',
  website: '',
};

export function ReservarPage() {
  const [params] = useSearchParams();
  const catalogue = useCatalogue();
  const [serviceId, setServiceId] = useState(params.get('servicio') ?? '');
  const [practitioners, setPractitioners] = useState<PublicPractitioner[]>([]);
  const [practitionersLoading, setPractitionersLoading] = useState(true);
  const [practitionersError, setPractitionersError] = useState(false);
  const [practitionerId, setPractitionerId] = useState('');
  const [date, setDate] = useState(localDate());
  const [slots, setSlots] = useState<AvailableSlot[]>([]);
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [slotsError, setSlotsError] = useState(false);
  const [selectedSlot, setSelectedSlot] = useState('');
  const [contact, setContact] = useState(EMPTY_CONTACT);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null);
  const [attempt, setAttempt] = useState(0);
  const service = catalogue.services.find((item) => item.id === serviceId);
  const professional = practitioners.find((item) => item.id === practitionerId);

  useEffect(() => {
    let active = true;
    setPractitionersError(false);
    setPractitionersLoading(true);
    apiFetch<PublicPractitioner[]>('/api/v1/public/practitioners')
      .then((data) => {
        if (active) setPractitioners(data);
      })
      .catch(() => {
        if (active) setPractitionersError(true);
      })
      .finally(() => {
        if (active) setPractitionersLoading(false);
      });
    return () => {
      active = false;
    };
  }, [attempt]);

  useEffect(() => {
    let active = true;
    setSelectedSlot('');
    setSlots([]);
    setSlotsError(false);
    setSlotsLoading(false);
    if (!serviceId || !practitionerId || !date) return;
    setSlotsLoading(true);
    const query = new URLSearchParams({
      treatment_definition_id: serviceId,
      practitioner_id: practitionerId,
      date_from: date,
      date_to: date,
    });
    apiFetch<AvailableSlot[]>(`/api/v1/public/availability?${query}`)
      .then((data) => {
        if (active) setSlots(data);
      })
      .catch(() => {
        if (active) setSlotsError(true);
      })
      .finally(() => {
        if (active) setSlotsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [serviceId, practitionerId, date, attempt]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!service || !professional || !selectedSlot) return;
    setSubmitting(true);
    setError('');
    try {
      const result = await apiFetch<Confirmation>('/api/v1/public/appointments', {
        method: 'POST',
        body: JSON.stringify({
          ...contact,
          first_name: contact.first_name.trim(),
          last_name: contact.last_name.trim(),
          phone_number: contact.phone_number.trim(),
          email: contact.email.trim() || null,
          message: contact.message.trim() || null,
          treatment_definition_id: serviceId,
          practitioner_id: practitionerId,
          starts_at: selectedSlot,
        }),
      });
      setConfirmation(result);
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 409) {
        setError('Ese horario acaba de ocuparse. Elige otro horario disponible para continuar.');
        setAttempt((value) => value + 1);
      } else if (cause instanceof ApiError && cause.status === 429) {
        setError('Recibimos demasiadas solicitudes. Espera unos minutos e inténtalo de nuevo.');
      } else {
        setError('No pudimos confirmar la cita. Revisa tus datos y vuelve a intentarlo.');
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (confirmation)
    return (
      <SimplePage title="Tu cita está confirmada">
        <div className="booking-confirmation" role="status">
          <p className="eyebrow">Reserva completada</p>
          <h2>{confirmation.treatment_name}</h2>
          <p>
            <strong>{formatAppointment(confirmation.starts_at)}</strong>
          </p>
          <p>Con {confirmation.practitioner_name} · Hora de Colombia</p>
          {service && (
            <p>
              {formatPrice(service.price, service.currency)} {service.currency} ·{' '}
              {service.duration_minutes} minutos
            </p>
          )}
          <p>{confirmation.detail}</p>
          <p className="booking-reference">Referencia: {confirmation.id}</p>
          <p>
            Guarda esta confirmación. Para cambiar o cancelar la cita, comunícate con el equipo e
            indica tu referencia.
          </p>
        </div>
        <Link to="/" className="button button--primary">
          Volver al inicio
        </Link>
      </SimplePage>
    );

  return (
    <SimplePage title="Reserva tu cita">
      <p>
        Elige un servicio, profesional y horario. Tu cita quedará reservada al confirmar. Todos los
        horarios corresponden a Colombia (UTC−5).
      </p>
      <form className="booking-form" onSubmit={handleSubmit}>
        <fieldset disabled={submitting} className="booking-step">
          <legend>1. Tu servicio y profesional</legend>
          <div className="booking-form__field">
            <label htmlFor="service" className="booking-form__label">
              Servicio
            </label>
            <select
              id="service"
              required
              className="booking-form__select"
              value={serviceId}
              onChange={(event) => {
                setServiceId(event.target.value);
                setSelectedSlot('');
              }}
              disabled={catalogue.loading || catalogue.error}
            >
              <option value="">
                {catalogue.loading ? 'Cargando servicios…' : 'Selecciona un servicio'}
              </option>
              {catalogue.services.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name} · {formatPrice(item.price, item.currency)} {item.currency} ·{' '}
                  {item.duration_minutes} min
                </option>
              ))}
            </select>
            {catalogue.error && (
              <p role="alert">
                No pudimos cargar los servicios.{' '}
                <button type="button" onClick={catalogue.retry} className="text-link">
                  Reintentar
                </button>
              </p>
            )}
            {!catalogue.loading && !catalogue.error && !catalogue.services.length && (
              <p>Aún no hay servicios disponibles para reservar.</p>
            )}
          </div>
          <div className="booking-form__field">
            <label htmlFor="professional" className="booking-form__label">
              Profesional
            </label>
            <select
              id="professional"
              required
              className="booking-form__select"
              value={practitionerId}
              onChange={(event) => {
                setPractitionerId(event.target.value);
                setSelectedSlot('');
              }}
              disabled={practitionersLoading || practitionersError}
            >
              <option value="">
                {practitionersLoading ? 'Cargando profesionales…' : 'Selecciona un profesional'}
              </option>
              {practitioners.map((person) => (
                <option key={person.id} value={person.id}>
                  {person.full_name}
                  {person.specialty ? ` · ${person.specialty}` : ''}
                </option>
              ))}
            </select>
            {practitionersError && (
              <p role="alert">
                No pudimos cargar el equipo.{' '}
                <button
                  type="button"
                  className="text-link"
                  onClick={() => setAttempt((value) => value + 1)}
                >
                  Reintentar
                </button>
              </p>
            )}
            {!practitionersLoading && !practitionersError && !practitioners.length && (
              <p>Aún no hay profesionales disponibles.</p>
            )}
          </div>
        </fieldset>
        <fieldset disabled={submitting} className="booking-step">
          <legend>2. Fecha y hora</legend>
          <div className="booking-form__field">
            <label htmlFor="appointment-date" className="booking-form__label">
              Fecha
            </label>
            <input
              id="appointment-date"
              type="date"
              min={localDate()}
              required
              className="booking-form__input"
              value={date}
              onChange={(event) => {
                setDate(event.target.value);
                setSelectedSlot('');
              }}
            />
          </div>
          {!serviceId || !practitionerId ? (
            <p>Selecciona un servicio y profesional para ver los horarios.</p>
          ) : (
            <>
              {slotsLoading && <p role="status">Consultando horarios…</p>}
              {slotsError && (
                <p role="alert">
                  No pudimos cargar los horarios.{' '}
                  <button
                    type="button"
                    className="text-link"
                    onClick={() => setAttempt((value) => value + 1)}
                  >
                    Reintentar
                  </button>
                </p>
              )}
              {!slotsLoading && !slotsError && slots.length === 0 && (
                <p role="status">
                  No hay horarios disponibles para esta fecha. Prueba otro día o profesional.
                </p>
              )}
              <div className="booking-slots" role="group" aria-label="Horarios disponibles">
                {slots.map((slot) => (
                  <button
                    key={slot.starts_at}
                    type="button"
                    aria-pressed={selectedSlot === slot.starts_at}
                    className={`booking-slot${selectedSlot === slot.starts_at ? ' booking-slot--selected' : ''}`}
                    onClick={() => setSelectedSlot(slot.starts_at)}
                  >
                    {new Intl.DateTimeFormat('es-CO', {
                      hour: '2-digit',
                      minute: '2-digit',
                      timeZone: 'America/Bogota',
                    }).format(new Date(slot.starts_at))}
                  </button>
                ))}
              </div>
            </>
          )}
        </fieldset>
        <fieldset disabled={submitting} className="booking-step">
          <legend>3. Tus datos</legend>
          <div className="booking-form__row">
            {(['first_name', 'last_name'] as const).map((key) => (
              <div className="booking-form__field" key={key}>
                <label htmlFor={key} className="booking-form__label">
                  {key === 'first_name' ? 'Nombre' : 'Apellido'}
                </label>
                <input
                  id={key}
                  autoComplete={key === 'first_name' ? 'given-name' : 'family-name'}
                  required
                  maxLength={150}
                  className="booking-form__input"
                  value={contact[key]}
                  onChange={(event) => setContact({ ...contact, [key]: event.target.value })}
                />
              </div>
            ))}
          </div>
          <div className="booking-form__row">
            <div className="booking-form__field">
              <label htmlFor="phone_number" className="booking-form__label">
                Teléfono
              </label>
              <input
                id="phone_number"
                type="tel"
                autoComplete="tel"
                required
                minLength={7}
                maxLength={30}
                placeholder="+57 300 000 0000"
                className="booking-form__input"
                value={contact.phone_number}
                onChange={(event) => setContact({ ...contact, phone_number: event.target.value })}
              />
            </div>
            <div className="booking-form__field">
              <label htmlFor="email" className="booking-form__label">
                Correo (opcional)
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                maxLength={320}
                className="booking-form__input"
                value={contact.email}
                onChange={(event) => setContact({ ...contact, email: event.target.value })}
              />
            </div>
          </div>
          <div className="booking-form__field">
            <label htmlFor="message" className="booking-form__label">
              Mensaje para coordinar la cita (opcional)
            </label>
            <textarea
              id="message"
              rows={2}
              maxLength={2000}
              className="booking-form__textarea"
              value={contact.message}
              onChange={(event) => setContact({ ...contact, message: event.target.value })}
            />
            <small>No incluyas información médica en este mensaje.</small>
          </div>
        </fieldset>
        <div className="booking-form__honeypot" aria-hidden="true">
          <label htmlFor="website">Sitio web</label>
          <input
            id="website"
            tabIndex={-1}
            autoComplete="off"
            value={contact.website}
            onChange={(event) => setContact({ ...contact, website: event.target.value })}
          />
        </div>
        {service && selectedSlot && (
          <div className="booking-summary">
            <strong>{service.name}</strong>
            <p>
              {formatAppointment(selectedSlot)} · {professional?.full_name}
            </p>
            <p>
              {formatPrice(service.price, service.currency)} {service.currency} ·{' '}
              {service.duration_minutes} minutos
            </p>
          </div>
        )}
        <p className="booking-privacy">
          Al reservar aceptas el uso de tus datos para gestionar esta cita según nuestra{' '}
          <Link to="/politica-de-privacidad" className="text-link">
            política de privacidad
          </Link>
          .
        </p>
        {error && (
          <p role="alert" className="booking-form__status booking-form__status--error">
            {error}
          </p>
        )}
        <button
          type="submit"
          className="button button--primary"
          disabled={submitting || !selectedSlot || !service || !professional}
        >
          {submitting ? 'Confirmando…' : 'Confirmar cita'}
        </button>
      </form>
    </SimplePage>
  );
}
