import { Link } from 'react-router-dom';

const LINKS = [
  { to: '/servicios', label: 'Servicios' },
  { to: '/tratamientos', label: 'Tratamientos' },
  { to: '/profesionales', label: 'Profesionales' },
  { to: '/preguntas-frecuentes', label: 'FAQ' },
  { to: '/contacto', label: 'Contacto' },
];

export function NavBar() {
  return (
    <header className="border-b border-slate-100">
      <nav className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <Link to="/" className="text-lg font-bold text-slate-900">
          Medical Platform
        </Link>
        <div className="hidden gap-6 text-sm font-medium text-slate-600 md:flex">
          {LINKS.map((link) => (
            <Link key={link.to} to={link.to} className="hover:text-slate-900">
              {link.label}
            </Link>
          ))}
        </div>
        <Link
          to="/reservar"
          className="rounded-full bg-slate-900 px-5 py-2 text-sm font-semibold text-white"
        >
          Reservar cita
        </Link>
      </nav>
    </header>
  );
}
