import { PageHeading } from '../../shared/components/app-shell';

export function DashboardPage() {
  return (
    <div>
      <PageHeading>Dashboard</PageHeading>
      <p className="text-slate-600">
        Resumen operativo del día: citas próximas, consentimientos pendientes y notificaciones
        recientes.
      </p>
    </div>
  );
}
