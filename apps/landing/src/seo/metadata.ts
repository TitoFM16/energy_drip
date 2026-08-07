export const DEFAULT_SITE_URL = 'http://localhost:5175';
export const SOCIAL_IMAGE_PATH = '/brand/energy-drip-home-care.webp';
export const SOCIAL_IMAGE_ALT =
  'Profesional de Energy Drip atendiendo a una paciente en su domicilio';

export type SeoPage = {
  path: string;
  canonicalPath: string;
  title: string;
  description: string;
  structuredData?: 'medical-business';
};

export const SEO_PAGES: readonly SeoPage[] = [
  {
    path: '/',
    canonicalPath: '/',
    title: 'Energy Drip Medellín | Terapias IV a domicilio',
    description:
      'Energy Drip Medellín: terapias IV móviles con valoración profesional y seguimiento personalizado en tu domicilio, hotel o Airbnb.',
    structuredData: 'medical-business',
  },
  {
    path: '/servicios',
    canonicalPath: '/servicios/',
    title: 'Servicios a domicilio | Energy Drip Medellín',
    description:
      'Energy Drip lleva una experiencia de bienestar personalizada a domicilios, hoteles y alojamientos dentro de su cobertura en Medellín.',
  },
  {
    path: '/tratamientos',
    canonicalPath: '/tratamientos/',
    title: 'Tratamientos personalizados | Energy Drip Medellín',
    description:
      'Conoce las líneas de tratamiento de Energy Drip. La composición, indicación y elegibilidad se definen después de una valoración profesional.',
  },
  {
    path: '/profesionales',
    canonicalPath: '/profesionales/',
    title: 'Cuidado profesional | Energy Drip Medellín',
    description:
      'Cada experiencia Energy Drip comienza con una revisión responsable de tu información y el acompañamiento de personal autorizado.',
  },
  {
    path: '/seguridad-y-privacidad',
    canonicalPath: '/seguridad-y-privacidad/',
    title: 'Seguridad y privacidad | Energy Drip Medellín',
    description:
      'Conoce cómo Energy Drip protege tu información médica con almacenamiento cifrado, acceso restringido y un historial de auditoría.',
  },
  {
    path: '/preguntas-frecuentes',
    canonicalPath: '/preguntas-frecuentes/',
    title: 'Preguntas frecuentes | Energy Drip Medellín',
    description:
      'Respuestas sobre el consentimiento previo, la firma desde el celular y la revisión profesional antes de confirmar un tratamiento.',
  },
  {
    path: '/contacto',
    canonicalPath: '/contacto/',
    title: 'Contacto | Energy Drip Medellín',
    description:
      'Cuéntanos qué tipo de atención buscas y dónde te encuentras. Confirmaremos cobertura y disponibilidad antes de solicitar información médica.',
  },
  {
    path: '/reservar',
    canonicalPath: '/reservar/',
    title: 'Reserva tu valoración | Energy Drip Medellín',
    description:
      'Solicita una valoración de Energy Drip. Indica el tratamiento que te interesa y un miembro del equipo confirmará disponibilidad y próximos pasos.',
  },
  {
    path: '/terminos',
    canonicalPath: '/terminos/',
    title: 'Términos y condiciones | Energy Drip Medellín',
    description: 'Términos de uso del servicio de agendamiento y atención médica de Energy Drip.',
  },
  {
    path: '/politica-de-privacidad',
    canonicalPath: '/politica-de-privacidad/',
    title: 'Política de privacidad | Energy Drip Medellín',
    description:
      'Consulta cómo Energy Drip recolecta, usa y protege tus datos personales y de salud.',
  },
];

export function normalizeSiteUrl(value: string): string {
  return value.replace(/\/+$/, '');
}

export function normalizeRoutePath(pathname: string): string {
  if (pathname === '/') return pathname;
  return pathname.replace(/\/+$/, '');
}

export function getSeoPage(pathname: string): SeoPage {
  const normalizedPath = normalizeRoutePath(pathname);
  return SEO_PAGES.find((page) => page.path === normalizedPath) ?? SEO_PAGES[0];
}

export function toAbsoluteUrl(siteUrl: string, path: string): string {
  return `${normalizeSiteUrl(siteUrl)}${path.startsWith('/') ? path : `/${path}`}`;
}

export function createMedicalBusinessStructuredData(siteUrl: string) {
  const normalizedSiteUrl = normalizeSiteUrl(siteUrl);

  return {
    '@context': 'https://schema.org',
    '@type': ['MedicalBusiness', 'LocalBusiness'],
    name: 'Energy Drip Medellín',
    url: `${normalizedSiteUrl}/`,
    image: toAbsoluteUrl(normalizedSiteUrl, SOCIAL_IMAGE_PATH),
    description: SEO_PAGES[0].description,
    address: {
      '@type': 'PostalAddress',
      addressLocality: 'Medellín',
      addressCountry: 'CO',
    },
    areaServed: 'Medellín',
    serviceType: ['Terapias IV móviles', 'Sueroterapia a domicilio', 'Valoración profesional'],
    knowsLanguage: ['es', 'en'],
  };
}
