import { PageHeading } from '../../shared/components/app-shell';
import { ReviewSection } from './review-section';
import { TemplatesSection } from './templates-section';

export function ConsentsPage() {
  return (
    <div>
      <PageHeading>Consentimientos</PageHeading>
      <TemplatesSection />
      <ReviewSection />
    </div>
  );
}
