import type { HTMLAttributes } from 'react';

type CalloutVariant = 'success' | 'warning' | 'danger';

// Matches the inline message-box markup already duplicated across
// staff-web (password-reset success banner, consent-answer warning notes)
// before this component existed.
const VARIANT_CLASSES: Record<CalloutVariant, string> = {
  success: 'bg-green-50 text-green-700',
  warning: 'bg-amber-50 text-amber-800',
  danger: 'bg-red-50 text-red-700',
};

export interface CalloutProps extends HTMLAttributes<HTMLParagraphElement> {
  variant: CalloutVariant;
}

export function Callout({ variant, className = '', ...props }: CalloutProps) {
  return (
    <p className={`rounded-lg p-3 text-sm ${VARIANT_CLASSES[variant]} ${className}`} {...props} />
  );
}
