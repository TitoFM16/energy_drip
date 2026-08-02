import type { ReactNode } from 'react';
import { Outlet } from 'react-router-dom';
import { Footer } from './footer';
import { NavBar } from './nav-bar';

export function PageLayout() {
  return (
    <div className="site-shell">
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
    <>
      <header className="page-hero">
        <p className="eyebrow">Energy Drip Medellín</p>
        <h1>{title}</h1>
        <span className="gold-rule" aria-hidden="true" />
      </header>
      <div className="simple-page">{children}</div>
    </>
  );
}
