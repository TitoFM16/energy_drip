import type { InputHTMLAttributes, TextareaHTMLAttributes } from 'react';

// Matches the <label>text<input/></label> markup already duplicated
// across essentially every form in staff-web (login, patient/practitioner
// CRUD, invite/password-reset flows, consent-template authoring) before
// this component existed — the label text is a direct child of <label>,
// not a separate element, which is what makes clicking the label text
// focus the input for free.
const LABEL_CLASSES = 'flex flex-col gap-1 text-sm font-medium text-slate-700';
const INPUT_CLASSES = 'rounded-lg border border-slate-300 px-3 py-2 text-sm';
const ERROR_TEXT_CLASSES = 'text-sm font-normal text-red-600';

export interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  containerClassName?: string;
}

export function TextField({
  label,
  error,
  containerClassName = '',
  className = '',
  ...props
}: TextFieldProps) {
  return (
    <label className={`${LABEL_CLASSES} ${containerClassName}`}>
      {label}
      <input className={`${INPUT_CLASSES} ${className}`} {...props} />
      {error && <span className={ERROR_TEXT_CLASSES}>{error}</span>}
    </label>
  );
}

export interface TextAreaFieldProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
  error?: string;
  containerClassName?: string;
}

export function TextAreaField({
  label,
  error,
  containerClassName = '',
  className = '',
  ...props
}: TextAreaFieldProps) {
  return (
    <label className={`${LABEL_CLASSES} ${containerClassName}`}>
      {label}
      <textarea className={`${INPUT_CLASSES} ${className}`} {...props} />
      {error && <span className={ERROR_TEXT_CLASSES}>{error}</span>}
    </label>
  );
}
