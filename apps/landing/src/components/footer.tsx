import { Link } from 'react-router-dom';
import { BrandMark } from './brand-mark';

export function Footer() {
  return (
    <footer className="site-footer">
      <div className="site-footer__inner">
        <div className="site-footer__brand">
          <BrandMark light />
          <p>Elige tu servicio, profesional y horario en un solo lugar.</p>
        </div>
        <div className="site-footer__nav">
          <p className="eyebrow eyebrow--light">Explora</p>
          <Link to="/servicios">Servicios</Link>
          <Link to="/reservar">Reservar una cita</Link>
        </div>
        <div className="site-footer__nav">
          <p className="eyebrow eyebrow--light">Información</p>
          <Link to="/seguridad-y-privacidad">Seguridad y privacidad</Link>
          <Link to="/politica-de-privacidad">Política de privacidad</Link>
          <Link to="/terminos">Términos</Link>
        </div>
      </div>
      <div className="site-footer__bottom">
        <span>© {new Date().getFullYear()} Energy Drip Medellín</span>
        <span>Tu bienestar, nuestra fórmula.</span>
      </div>
    </footer>
  );
}
