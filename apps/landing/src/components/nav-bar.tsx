import { Link } from 'react-router-dom';
import { BrandMark } from './brand-mark';

const LINKS = [
  { to: '/servicios', label: 'Servicios' },
  { to: '/tratamientos', label: 'Tratamientos' },
  { to: '/profesionales', label: 'Profesionales' },
  { to: '/preguntas-frecuentes', label: 'FAQ' },
  { to: '/contacto', label: 'Contacto' },
];

export function NavBar() {
  return (
    <header className="site-header">
      <div className="site-header__note">
        <span>Premium mobile IV therapy</span>
        <span className="site-header__note-separator" aria-hidden="true" />
        <span>Medellín, Colombia</span>
      </div>
      <nav className="site-nav" aria-label="Navegación principal">
        <BrandMark />
        <div className="site-nav__links">
          {LINKS.map((link) => (
            <Link key={link.to} to={link.to}>
              {link.label}
            </Link>
          ))}
        </div>
        <Link to="/reservar" className="button button--primary site-nav__cta">
          Reservar
        </Link>
      </nav>
    </header>
  );
}
