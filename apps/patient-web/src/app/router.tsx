import { createBrowserRouter, Navigate } from 'react-router-dom';
import { CompletedPage } from '../routes/completed';
import { ConsentStartPage } from '../routes/consent-start';
import { MedicalQuestionnairePage } from '../routes/medical-questionnaire';
import { ReviewPage } from '../routes/review';
import { SignaturePage } from '../routes/signature';
import { TreatmentInformationPage } from '../routes/treatment-information';
import { MobileShell } from '../shared/mobile-shell';

export const router = createBrowserRouter([
  {
    path: '/c/:token',
    element: (
      <MobileShell>
        <ConsentStartPage />
      </MobileShell>
    ),
  },
  {
    path: '/c/:token/questionnaire',
    element: (
      <MobileShell>
        <MedicalQuestionnairePage />
      </MobileShell>
    ),
  },
  {
    path: '/c/:token/treatment-information',
    element: (
      <MobileShell>
        <TreatmentInformationPage />
      </MobileShell>
    ),
  },
  {
    path: '/c/:token/signature',
    element: (
      <MobileShell>
        <SignaturePage />
      </MobileShell>
    ),
  },
  {
    path: '/c/:token/review',
    element: (
      <MobileShell>
        <ReviewPage />
      </MobileShell>
    ),
  },
  {
    path: '/c/:token/completed',
    element: (
      <MobileShell>
        <CompletedPage />
      </MobileShell>
    ),
  },
  { path: '*', element: <Navigate to="/c/invalid" replace /> },
]);
