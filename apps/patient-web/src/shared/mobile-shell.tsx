import type { ReactNode } from 'react';

export function MobileShell({ children }: { children: ReactNode }) {
  return <div className="mx-auto min-h-screen max-w-md bg-slate-50 px-5 py-8">{children}</div>;
}
