import { SimplePage } from '../components/page-layout';

export function SeguridadYPrivacidadPage() {
  return (
    <SimplePage title="Tu información merece cuidado">
      <p>
        Tu información médica se almacena cifrada y con acceso restringido por roles. Cada consulta
        y modificación queda registrada en un historial de auditoría.
      </p>
      <p className="simple-page__note">
        Antes de compartir información de salud, verifica que estés usando el enlace privado enviado
        por Energy Drip. No solicitamos antecedentes médicos por redes sociales.
      </p>
    </SimplePage>
  );
}
