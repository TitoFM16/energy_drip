import { useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { SimplePage } from '../components/page-layout';
import { buildBookingRequestPayload } from '../features/booking/build-payload';
import { apiFetch, ApiError } from '../shared/api';

interface PublicTreatment {
  id: string;
  name: string;
  description: string | null;
}

type SubmitState =
  | { status: 'idle' }
  | { status: 'submitting' }
  | { status: 'success'; message: string }
  | { status: 'error'; message: string };

const INITIAL_FORM = {
  first_name: '',
  last_name: '',
  phone_number: '',
  email: '',
  treatment_definition_id: '',
  preferred_date: '',
  message: '',
  // Honeypot — real visitors never see this field (hidden off-screen
  // below), so it must stay empty. A bot filling in every input in the
  // DOM will trip it. See BookingRequestService.create_request on the API
  // side for what happens when it's non-empty.
  website: '',
};

export function ReservarPage() {
  const [treatments, setTreatments] = useState<PublicTreatment[]>([]);
  const [treatmentsError, setTreatmentsError] = useState(false);
  const [form, setForm] = useState(INITIAL_FORM);
  const [submitState, setSubmitState] = useState<SubmitState>({ status: 'idle' });

  useEffect(() => {
    apiFetch<PublicTreatment[]>('/api/v1/public/treatments')
      .then(setTreatments)
      .catch(() => setTreatmentsError(true));
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitState({ status: 'submitting' });
    try {
      const response = await apiFetch<{ detail: string }>('/api/v1/public/booking-requests', {
        method: 'POST',
        body: JSON.stringify(buildBookingRequestPayload(form)),
      });
      setSubmitState({ status: 'success', message: response.detail });
      setForm(INITIAL_FORM);
    } catch (error) {
      if (error instanceof ApiError && error.status === 429) {
        setSubmitState({
          status: 'error',
          message:
            'Recibimos demasiadas solicitudes desde tu conexión. Intenta de nuevo más tarde.',
        });
      } else {
        setSubmitState({
          status: 'error',
          message: 'No pudimos enviar tu solicitud. Intenta de nuevo o escríbenos directamente.',
        });
      }
    }
  }

  if (submitState.status === 'success') {
    return (
      <SimplePage title="Reserva tu valoración">
        <div>
          <h3>Solicitud recibida</h3>
          <p>{submitState.message}</p>
        </div>
        <Link to="/" className="button button--primary">
          Volver al inicio
        </Link>
      </SimplePage>
    );
  }

  return (
    <SimplePage title="Reserva tu valoración">
      <p>
        Cuéntanos qué tratamiento te interesa y cómo contactarte. Un miembro del equipo confirmará
        disponibilidad y te compartirá los siguientes pasos — nunca compartimos antecedentes médicos
        ni documentos por este formulario.
      </p>
      <form className="booking-form" onSubmit={handleSubmit} noValidate>
        <div className="booking-form__row">
          <div className="booking-form__field">
            <label className="booking-form__label" htmlFor="first_name">
              Nombre
            </label>
            <input
              id="first_name"
              className="booking-form__input"
              required
              maxLength={150}
              value={form.first_name}
              onChange={(e) => setForm({ ...form, first_name: e.target.value })}
            />
          </div>
          <div className="booking-form__field">
            <label className="booking-form__label" htmlFor="last_name">
              Apellido
            </label>
            <input
              id="last_name"
              className="booking-form__input"
              required
              maxLength={150}
              value={form.last_name}
              onChange={(e) => setForm({ ...form, last_name: e.target.value })}
            />
          </div>
        </div>

        <div className="booking-form__row">
          <div className="booking-form__field">
            <label className="booking-form__label" htmlFor="phone_number">
              Teléfono (WhatsApp)
            </label>
            <input
              id="phone_number"
              className="booking-form__input"
              type="tel"
              required
              placeholder="+57 300 000 0000"
              maxLength={30}
              value={form.phone_number}
              onChange={(e) => setForm({ ...form, phone_number: e.target.value })}
            />
          </div>
          <div className="booking-form__field">
            <label className="booking-form__label" htmlFor="email">
              Correo (opcional)
            </label>
            <input
              id="email"
              className="booking-form__input"
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </div>
        </div>

        <div className="booking-form__field">
          <label className="booking-form__label" htmlFor="treatment_definition_id">
            Tratamiento de interés
          </label>
          <select
            id="treatment_definition_id"
            className="booking-form__select"
            required
            value={form.treatment_definition_id}
            onChange={(e) => setForm({ ...form, treatment_definition_id: e.target.value })}
            disabled={treatmentsError || treatments.length === 0}
          >
            <option value="" disabled>
              {treatmentsError
                ? 'No disponible en este momento'
                : treatments.length === 0
                  ? 'Cargando tratamientos…'
                  : 'Selecciona un tratamiento'}
            </option>
            {treatments.map((treatment) => (
              <option key={treatment.id} value={treatment.id}>
                {treatment.name}
              </option>
            ))}
          </select>
        </div>

        <div className="booking-form__field">
          <label className="booking-form__label" htmlFor="preferred_date">
            Fecha de preferencia (opcional)
          </label>
          <input
            id="preferred_date"
            className="booking-form__input"
            type="date"
            value={form.preferred_date}
            onChange={(e) => setForm({ ...form, preferred_date: e.target.value })}
          />
        </div>

        <div className="booking-form__field">
          <label className="booking-form__label" htmlFor="message">
            Mensaje (opcional)
          </label>
          <textarea
            id="message"
            className="booking-form__textarea"
            rows={3}
            maxLength={2000}
            value={form.message}
            onChange={(e) => setForm({ ...form, message: e.target.value })}
          />
        </div>

        {/* Honeypot: hidden from sighted and screen-reader users alike,
            never tabbable. A human never fills this in. */}
        <div className="booking-form__honeypot" aria-hidden="true">
          <label htmlFor="website">Sitio web</label>
          <input
            id="website"
            name="website"
            tabIndex={-1}
            autoComplete="off"
            value={form.website}
            onChange={(e) => setForm({ ...form, website: e.target.value })}
          />
        </div>

        {submitState.status === 'error' && (
          <p className="booking-form__status booking-form__status--error">{submitState.message}</p>
        )}

        <button
          type="submit"
          className="button button--primary"
          disabled={submitState.status === 'submitting' || treatmentsError}
        >
          {submitState.status === 'submitting' ? 'Enviando…' : 'Enviar solicitud'}
        </button>
      </form>
      <div className="simple-page__note">
        Nunca envíes antecedentes médicos, documentos de identidad ni otra información sensible por
        este formulario ni por redes sociales. El equipo te compartirá un enlace privado cuando
        corresponda.
      </div>
    </SimplePage>
  );
}
