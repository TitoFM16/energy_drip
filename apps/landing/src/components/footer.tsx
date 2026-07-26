import { Link } from 'react-router-dom';

export function Footer() {
  return (
    <footer className="border-t border-slate-100 py-8">
      <div className="mx-auto flex max-w-5xl flex-col gap-3 px-6 text-sm text-slate-500 md:flex-row md:justify-between">
        <span>© {new Date().getFullYear()} Medical Platform</span>
        <div className="flex gap-4">
          <Link to="/seguridad-y-privacidad">Seguridad y privacidad</Link>
          <Link to="/politica-de-privacidad">Política de privacidad</Link>
          <Link to="/terminos">Términos</Link>
        </div>
      </div>
    </footer>
  );
}
