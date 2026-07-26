import { Link } from 'react-router-dom';
import { SERVICES } from '../content/services';

export function HomePage() {
  return (
    <div>
      <section className="mx-auto flex max-w-5xl flex-col items-start gap-6 px-6 py-24">
        <h1 className="max-w-2xl text-4xl font-bold tracking-tight text-slate-900 md:text-5xl">
          Citas médicas a demanda, sin filas ni papeleo
        </h1>
        <p className="max-w-xl text-lg text-slate-600">
          Agenda tu cita, completa tu filtro médico y firma tu consentimiento desde el celular —
          todo antes de llegar a la clínica.
        </p>
        <Link
          to="/reservar"
          className="rounded-full bg-slate-900 px-6 py-3 text-base font-semibold text-white"
        >
          Reservar mi cita
        </Link>
      </section>
      <section className="mx-auto max-w-5xl px-6 py-16">
        <div className="grid gap-8 md:grid-cols-3">
          {SERVICES.map((service) => (
            <div key={service.title} className="rounded-xl border border-slate-100 p-6">
              <h3 className="mb-2 text-lg font-semibold text-slate-900">{service.title}</h3>
              <p className="text-sm text-slate-600">{service.description}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
