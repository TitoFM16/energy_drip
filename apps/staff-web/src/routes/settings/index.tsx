import { PageHeading } from '../../shared/components/app-shell';
import { AvailabilityRulesSection } from './availability-rules-section';
import { PractitionersSection } from './practitioners-section';

export function SettingsPage() {
  return (
    <div>
      <PageHeading>Equipo y horarios</PageHeading>
      <p className="mb-6 text-slate-600">
        Agrega a las personas que prestan tus servicios y configura sus horarios semanales. Los
        horarios se muestran en hora de Colombia (UTC−5).
      </p>
      <PractitionersSection />
      <AvailabilityRulesSection />
    </div>
  );
}
