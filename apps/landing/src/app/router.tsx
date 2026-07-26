import { createBrowserRouter } from 'react-router-dom';
import { PageLayout } from '../components/page-layout';
import { ContactoPage } from '../pages/contacto';
import { HomePage } from '../pages/home';
import { PoliticaDePrivacidadPage } from '../pages/politica-de-privacidad';
import { PreguntasFrecuentesPage } from '../pages/preguntas-frecuentes';
import { ProfesionalesPage } from '../pages/profesionales';
import { ReservarPage } from '../pages/reservar';
import { SeguridadYPrivacidadPage } from '../pages/seguridad-y-privacidad';
import { ServiciosPage } from '../pages/servicios';
import { TerminosPage } from '../pages/terminos';
import { TratamientosPage } from '../pages/tratamientos';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <PageLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'servicios', element: <ServiciosPage /> },
      { path: 'tratamientos', element: <TratamientosPage /> },
      { path: 'profesionales', element: <ProfesionalesPage /> },
      { path: 'seguridad-y-privacidad', element: <SeguridadYPrivacidadPage /> },
      { path: 'preguntas-frecuentes', element: <PreguntasFrecuentesPage /> },
      { path: 'contacto', element: <ContactoPage /> },
      { path: 'reservar', element: <ReservarPage /> },
      { path: 'terminos', element: <TerminosPage /> },
      { path: 'politica-de-privacidad', element: <PoliticaDePrivacidadPage /> },
    ],
  },
]);
