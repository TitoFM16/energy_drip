import type { HTMLAttributes } from 'react';

// Matches the standalone error-message markup already duplicated across
// nearly every screen in staff-web — both query-load failures ("No se
// pudo cargar...") and mutation-submission failures ("No se pudo
// crear/guardar...") — before this component existed.
export function ErrorText({ className = '', ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return <p className={`text-sm text-red-600 ${className}`} {...props} />;
}
