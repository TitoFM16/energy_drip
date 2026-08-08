import { PageHeading } from '../../shared/components/app-shell';
import { AvailabilityRulesSection } from './availability-rules-section';
import { PractitionersSection } from './practitioners-section';
import { UserRolesSection } from './user-roles-section';

export function SettingsPage() {
  return (
    <div>
      <PageHeading>Configuración</PageHeading>
      <PractitionersSection />
      <AvailabilityRulesSection />
      <UserRolesSection />
    </div>
  );
}
