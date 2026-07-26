import { SERVICES } from '../content/services';
import { SimplePage } from '../components/page-layout';

export function ServiciosPage() {
  return (
    <SimplePage title="Servicios">
      {SERVICES.map((service) => (
        <div key={service.title}>
          <h3 className="font-semibold text-slate-900">{service.title}</h3>
          <p>{service.description}</p>
        </div>
      ))}
    </SimplePage>
  );
}
