import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { TREATMENT_GROUPS } from '../content/services';

const EXPERIENCES = [
  {
    icon: 'home',
    title: 'En tu domicilio',
    description: 'Una experiencia privada y tranquila, sin desplazamientos innecesarios.',
  },
  {
    icon: 'hotel',
    title: 'En tu hotel',
    description: 'Atención móvil pensada para viajeros y visitantes en Medellín.',
  },
  {
    icon: 'location',
    title: 'En tu Airbnb',
    description: 'Coordinamos la visita donde te estés hospedando dentro de nuestra cobertura.',
  },
];

const PROCESS = [
  ['01', 'Reserva tu valoración', 'Cuéntanos dónde estás y qué tipo de atención necesitas.'],
  ['02', 'Completa el filtro médico', 'Responde el formulario previo desde tu celular.'],
  ['03', 'Recibe atención personalizada', 'Un profesional revisa tu caso antes de cada sesión.'],
];

export function HomePage() {
  return (
    <div className="home-page">
      <section className="hero">
        <div className="hero__content">
          <p className="eyebrow">Sueroterapia premium a domicilio</p>
          <h1>
            Recupera tu energía. <em>Vive Medellín al máximo.</em>
          </h1>
          <p className="hero__lead">
            Terapias IV móviles, valoración profesional y seguimiento personalizado en la comodidad
            de tu domicilio, hotel o Airbnb.
          </p>
          <div className="hero__actions">
            <Link to="/reservar" className="button button--primary">
              Reservar valoración
              <ArrowIcon />
            </Link>
            <Link to="/tratamientos" className="button button--quiet">
              Ver tratamientos
            </Link>
          </div>
          <div className="hero__trust" aria-label="Características del servicio">
            <span>
              <CheckIcon /> Profesionales certificados
            </span>
            <span>
              <CheckIcon /> Atención personalizada
            </span>
            <span>
              <CheckIcon /> Español e inglés
            </span>
          </div>
        </div>
        <div className="hero__visual">
          <img
            src="/brand/energy-drip-home-care.webp"
            alt="Profesional de Energy Drip atendiendo a una paciente en su domicilio"
          />
          <div className="hero__image-note">
            <span>Medellín</span>
            <strong>Bienestar donde estés</strong>
          </div>
        </div>
      </section>

      <section className="promise-strip" aria-label="Nuestra propuesta de bienestar">
        <Promise icon="drop" label="Hidratación" />
        <Promise icon="bolt" label="Energía" />
        <Promise icon="shield" label="Bienestar" />
        <Promise icon="heart" label="Recuperación" />
      </section>

      <section className="section treatments-preview">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Nuestros tratamientos</p>
            <h2>Una fórmula para cada momento</h2>
          </div>
          <p>
            Cada protocolo se define después de una valoración profesional. Explora nuestras líneas
            de recuperación, bienestar y terapia premium.
          </p>
        </div>
        <div className="treatment-grid">
          {TREATMENT_GROUPS.map((group, index) => (
            <article className="treatment-card" key={group.title}>
              <span className="treatment-card__number">0{index + 1}</span>
              <Icon name={group.icon} />
              <p className="eyebrow">{group.kicker}</p>
              <h3>{group.title}</h3>
              <p>{group.description}</p>
              <ul>
                {group.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
        <Link to="/tratamientos" className="text-link">
          Conocer todos los tratamientos <ArrowIcon />
        </Link>
      </section>

      <section className="experience-section">
        <div className="experience-section__copy">
          <p className="eyebrow eyebrow--light">Te atendemos donde estés</p>
          <h2>El cuidado viene a ti</h2>
          <p>
            Diseñamos una experiencia discreta, cálida y coordinada alrededor de tu agenda. Nosotros
            nos desplazamos; tú eliges dónde sentirte mejor.
          </p>
          <Link to="/servicios" className="button button--gold">
            Explorar el servicio
          </Link>
        </div>
        <div className="experience-list">
          {EXPERIENCES.map((experience) => (
            <article key={experience.title}>
              <Icon name={experience.icon} />
              <div>
                <h3>{experience.title}</h3>
                <p>{experience.description}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="section process-section">
        <div className="section-heading section-heading--centered">
          <div>
            <p className="eyebrow">Simple, seguro y personalizado</p>
            <h2>Tu experiencia en tres pasos</h2>
          </div>
        </div>
        <div className="process-grid">
          {PROCESS.map(([number, title, description]) => (
            <article key={number}>
              <span>{number}</span>
              <h3>{title}</h3>
              <p>{description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="medical-note">
        <div className="medical-note__icon">
          <Icon name="medical" />
        </div>
        <div>
          <p className="eyebrow">Tu seguridad primero</p>
          <h2>Valoración antes de cada tratamiento</h2>
          <p>
            Antes de confirmar una sesión revisamos tus antecedentes y respuestas al filtro médico.
            La elegibilidad y el protocolo final siempre los determina el profesional tratante.
          </p>
        </div>
        <Link to="/seguridad-y-privacidad" className="text-link">
          Cómo cuidamos tu información <ArrowIcon />
        </Link>
      </section>

      <section className="final-cta">
        <p className="eyebrow eyebrow--light">Energy Drip Medellín</p>
        <h2>Tu bienestar, nuestra fórmula.</h2>
        <p>Agenda tu valoración y recibe una experiencia de bienestar donde estés.</p>
        <Link to="/reservar" className="button button--gold">
          Quiero reservar <ArrowIcon />
        </Link>
      </section>
    </div>
  );
}

function Promise({ icon, label }: { icon: string; label: string }) {
  return (
    <div>
      <Icon name={icon} />
      <span>{label}</span>
    </div>
  );
}

function ArrowIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M5 12h14M14 6l6 6-6 6" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="m5 12 4 4L19 6" />
    </svg>
  );
}

function Icon({ name }: { name: string }) {
  const paths: Record<string, ReactNode> = {
    drop: <path d="M12 2S5 10.1 5 15a7 7 0 0 0 14 0c0-4.9-7-13-7-13Z" />,
    bolt: <path d="m13 2-8 12h7l-1 8 8-12h-7l1-8Z" />,
    shield: <path d="M12 3 4.5 6v5.5c0 4.7 3.2 8.1 7.5 9.5 4.3-1.4 7.5-4.8 7.5-9.5V6L12 3Z" />,
    heart: (
      <path d="M20.8 5.8a5.4 5.4 0 0 0-7.6 0L12 7l-1.2-1.2a5.4 5.4 0 1 0-7.6 7.6L12 22l8.8-8.6a5.4 5.4 0 0 0 0-7.6Z" />
    ),
    recovery: (
      <>
        <path d="M20 8a8 8 0 1 0 1 7" />
        <path d="M20 3v5h-5" />
      </>
    ),
    wellness: (
      <>
        <path d="M12 21c5-3.5 7.5-7 7.5-10.5A7.5 7.5 0 0 0 12 3a7.5 7.5 0 0 0-7.5 7.5C4.5 14 7 17.5 12 21Z" />
        <path d="M12 7v8M8 11h8" />
      </>
    ),
    premium: (
      <>
        <path d="m12 2 2.2 6.4L21 10l-5.2 4 1 7-4.8-3.2L7.2 21l1-7L3 10l6.8-1.6L12 2Z" />
      </>
    ),
    home: (
      <>
        <path d="m3 11 9-8 9 8" />
        <path d="M5.5 9.5V21h13V9.5M9.5 21v-7h5v7" />
      </>
    ),
    hotel: (
      <>
        <path d="M5 21V4h10v17M15 10h4v11M2 21h20" />
        <path d="M8 8h1M11 8h1M8 12h1M11 12h1" />
      </>
    ),
    location: (
      <>
        <path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z" />
        <circle cx="12" cy="10" r="2.5" />
      </>
    ),
    medical: (
      <>
        <path d="M7 3h10v18H7z" />
        <path d="M9 7h6M12 4v6M9.5 15h5" />
      </>
    ),
  };
  return (
    <svg aria-hidden="true" className="line-icon" viewBox="0 0 24 24">
      {paths[name]}
    </svg>
  );
}
