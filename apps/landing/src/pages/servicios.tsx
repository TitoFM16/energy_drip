import { ServiceCatalogue } from '../components/service-catalogue';
export function ServiciosPage() {
  return (
    <section className="section">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Energy Drip</p>
          <h1>Servicios y precios</h1>
        </div>
        <p>Elige tu servicio y reserva con nuestro equipo.</p>
      </div>
      <ServiceCatalogue />
    </section>
  );
}
