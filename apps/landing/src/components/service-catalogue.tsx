import { mediaUrl } from '../shared/api';
import { Link } from 'react-router-dom';
import { formatPrice, useCatalogue } from '../features/booking/catalogue';

export function ServiceCatalogue() {
  const { services, loading, error, retry } = useCatalogue();
  if (loading) return <p role="status">Cargando servicios…</p>;
  if (error)
    return (
      <div role="alert">
        <p>No pudimos cargar los servicios.</p>
        <button className="button button--quiet" type="button" onClick={retry}>
          Volver a intentar
        </button>
      </div>
    );
  if (!services.length)
    return <p>Pronto publicaremos nuestros servicios y horarios. Vuelve a visitarnos.</p>;
  return (
    <div className="service-grid">
      {services.map((service) => (
        <article className="service-card" key={service.id}>
          {service.image_url ? (
            <img src={mediaUrl(service.image_url)} alt={service.name} loading="lazy" />
          ) : (
            <div className="service-card__placeholder" aria-hidden="true">
              ✦
            </div>
          )}
          <div className="service-card__content">
            <p className="eyebrow">{service.duration_minutes} minutos</p>
            <h3>{service.name}</h3>
            <p>{service.description || 'Atención personalizada con nuestro equipo.'}</p>
            <div className="service-card__footer">
              <strong>
                {formatPrice(service.price, service.currency)} <small>{service.currency}</small>
              </strong>
              <Link className="button button--primary" to={`/reservar?servicio=${service.id}`}>
                Reservar
              </Link>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}
