import type { ReactNode } from 'react';
import { Outlet } from 'react-router-dom';
import { Footer } from './footer';
import { NavBar } from './nav-bar';

export function PageLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-white text-slate-900">
      <NavBar />
      <main className="flex-1">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}

export function SimplePage({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="mb-6 text-3xl font-bold text-slate-900">{title}</h1>
      <div className="flex flex-col gap-4 text-slate-600">{children}</div>
    </div>
  );
}
