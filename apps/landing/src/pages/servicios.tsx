import { Link } from 'react-router-dom';
import { SERVICES } from '../content/services';
import { SimplePage } from '../components/page-layout';

export function ServiciosPage() {
  return (
    <SimplePage title="Bienestar donde estés">
      <p>
        Energy Drip lleva una experiencia de bienestar personalizada a domicilios, hoteles y
        alojamientos dentro de nuestra cobertura en Medellín.
      </p>
      {SERVICES.map((service) => (
        <article key={service.title}>
          <h3>{service.title}</h3>
          <p>{service.description}</p>
        </article>
      ))}
      <Link to="/reservar" className="button button--primary">
        Reservar valoración
      </Link>
    </SimplePage>
  );
}
