import { Link } from 'react-router-dom';

export function BrandMark({ light = false }: { light?: boolean }) {
  return (
    <Link
      to="/"
      className={`brand-mark ${light ? 'brand-mark--light' : ''}`}
      aria-label="Energy Drip Medellín — Inicio"
    >
      <svg aria-hidden="true" viewBox="0 0 48 58" className="brand-mark__symbol">
        <path d="M24 2C17.5 12.2 6 25.1 6 37.5A18 18 0 0 0 42 37.5C42 25.1 30.5 12.2 24 2Z" />
        <path d="M12.5 37.5h6l3-8 5 16 3.5-8h5.5" />
      </svg>
      <span className="brand-mark__wordmark">
        <span>
          Energy <b>Drip</b>
        </span>
        <small>Medellín</small>
      </span>
    </Link>
  );
}
