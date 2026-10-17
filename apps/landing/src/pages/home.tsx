import { Link } from 'react-router-dom';
import { ServiceCatalogue } from '../components/service-catalogue';

export function HomePage() {
  return (
    <div className="home-page">
      <section className="hero">
        <div className="hero__content">
          <p className="eyebrow">Energy Drip · Medellín</p>
          <h1>
            Tu cuidado, <em>a tu tiempo.</em>
          </h1>
          <p className="hero__lead">
            Consulta nuestros servicios, elige al profesional y reserva el horario que mejor se
            ajuste a ti.
          </p>
          <div className="hero__actions">
            <a href="#servicios" className="button button--primary">
              Ver servicios y precios
            </a>
            <Link to="/reservar" className="button button--quiet">
              Reservar una cita →
            </Link>
          </div>
          <div className="hero__trust">
            <span>Precios visibles</span>
            <span>Horarios disponibles</span>
            <span>Reserva en minutos</span>
          </div>
        </div>
        <div className="hero__visual">
          <img
            src="/brand/energy-drip-home-care.webp"
            alt="Atención profesional en un ambiente tranquilo"
          />
          <div className="hero__image-note">
            <span>Atención personal</span>
            <strong>Un momento para cuidarte</strong>
          </div>
        </div>
      </section>
      <section id="servicios" className="section treatments-preview">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Nuestro catálogo</p>
            <h2>Servicios y precios</h2>
          </div>
          <p>
            Elige un servicio para consultar los profesionales y sus horarios disponibles. Todos los
            horarios corresponden a Colombia.
          </p>
        </div>
        <ServiceCatalogue />
      </section>
      <section className="section process-section">
        <div className="section-heading section-heading--centered">
          <div>
            <p className="eyebrow">Así de sencillo</p>
            <h2>Tu próxima cita, en tres pasos</h2>
          </div>
        </div>
        <div className="process-grid">
          <article>
            <span>01</span>
            <h3>Elige tu servicio</h3>
            <p>Consulta su descripción, duración y precio.</p>
          </article>
          <article>
            <span>02</span>
            <h3>Encuentra tu horario</h3>
            <p>Selecciona al profesional y una hora disponible.</p>
          </article>
          <article>
            <span>03</span>
            <h3>Confirma tu cita</h3>
            <p>Completa tus datos y guarda la confirmación de tu reserva.</p>
          </article>
        </div>
      </section>
    </div>
  );
}
