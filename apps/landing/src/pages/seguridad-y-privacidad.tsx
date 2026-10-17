import { Link } from 'react-router-dom';
import { SimplePage } from '../components/page-layout';

export function SeguridadYPrivacidadPage() {
  return (
    <SimplePage title="Tu información merece cuidado">
      <p>
        La reserva solicita los datos necesarios para coordinar tu cita. Los consentimientos se
        completan mediante enlaces privados y el personal autorizado los gestiona desde su panel.
      </p>
      <p className="simple-page__note">
        Antes de compartir información de salud, verifica que estés usando el enlace privado que te
        compartió el equipo. No publiques este enlace ni incluyas información médica en el mensaje
        de reserva.
      </p>
      <Link to="/politica-de-privacidad" className="text-link">
        Consultar el uso de tus datos
      </Link>
    </SimplePage>
  );
}
