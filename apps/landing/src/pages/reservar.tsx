import { Link } from 'react-router-dom';
import { SimplePage } from '../components/page-layout';

export function ReservarPage() {
  return (
    <SimplePage title="Reserva tu valoración">
      <p>
        Estamos preparando la reserva en línea. Mientras activamos el formulario, puedes conocer
        nuestros tratamientos o escribirnos a través de nuestros canales de atención.
      </p>
      <div className="simple-page__note">
        Nunca envíes antecedentes médicos, documentos de identidad ni otra información sensible por
        redes sociales. El equipo te compartirá un enlace privado cuando corresponda.
      </div>
      <Link to="/contacto" className="button button--primary">
        Ver canales de contacto
      </Link>
    </SimplePage>
  );
}
