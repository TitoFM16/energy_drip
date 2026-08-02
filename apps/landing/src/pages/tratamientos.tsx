import { Link } from 'react-router-dom';
import { SimplePage } from '../components/page-layout';
import { TREATMENT_GROUPS } from '../content/services';

export function TratamientosPage() {
  return (
    <SimplePage title="Tratamientos personalizados">
      <p>
        Conoce nuestras líneas de tratamiento. La composición, indicación y elegibilidad se definen
        únicamente después de una valoración profesional.
      </p>
      {TREATMENT_GROUPS.map((group) => (
        <article key={group.title}>
          <p className="eyebrow">{group.kicker}</p>
          <h3>{group.title}</h3>
          <p>{group.description}</p>
          <p>{group.items.join(' · ')}</p>
        </article>
      ))}
      <p className="simple-page__note">
        La información de esta página es orientativa y no reemplaza una consulta ni constituye una
        indicación médica. El profesional tratante determina si un protocolo es apropiado.
      </p>
      <Link to="/reservar" className="button button--primary">
        Solicitar valoración
      </Link>
    </SimplePage>
  );
}
