import { Link } from 'react-router-dom';
import { SimplePage } from '../components/page-layout';

export function ContactoPage() {
  return (
    <SimplePage title="Hablemos de tu bienestar">
      <p>
        Cuéntanos qué tipo de atención buscas y dónde te encuentras. Confirmaremos cobertura y
        disponibilidad antes de solicitar información médica.
      </p>
      <article>
        <p className="eyebrow">Redes</p>
        <h3>@energydripmedellin</h3>
        <p>Síguenos para conocer novedades y experiencias de Energy Drip en Medellín.</p>
      </article>
      <Link to="/reservar" className="button button--primary">
        Iniciar reserva
      </Link>
    </SimplePage>
  );
}
