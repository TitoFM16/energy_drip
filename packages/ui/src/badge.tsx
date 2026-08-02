import type { HTMLAttributes } from 'react';

type BadgeVariant = 'neutral' | 'success' | 'warning' | 'danger';

// Matches the status-pill markup already duplicated across staff-web
// (appointment status, consent-template publish state, etc.) before this
// component existed — `neutral` is the exact class set every one of those
// used by default; `success`/`warning`/`danger` match the one existing
// colored usage (published-template badge) and the design-tokens
// package's success/warning/danger palette.
const VARIANT_CLASSES: Record<BadgeVariant, string> = {
  neutral: 'bg-slate-100 text-slate-600',
  success: 'bg-green-50 text-green-700',
  warning: 'bg-amber-100 text-amber-800',
  danger: 'bg-red-50 text-red-700',
};

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

export function Badge({ variant = 'neutral', className = '', ...props }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${VARIANT_CLASSES[variant]} ${className}`}
      {...props}
    />
  );
}
