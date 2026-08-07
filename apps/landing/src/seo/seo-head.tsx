import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import {
  createMedicalBusinessStructuredData,
  DEFAULT_SITE_URL,
  getSeoPage,
  normalizeSiteUrl,
  SOCIAL_IMAGE_ALT,
  SOCIAL_IMAGE_PATH,
  toAbsoluteUrl,
} from './metadata';

const JSON_LD_ID = 'energy-drip-medical-business-jsonld';

function upsertMeta(attribute: 'name' | 'property', key: string, content: string) {
  let element = document.head.querySelector<HTMLMetaElement>(`meta[${attribute}="${key}"]`);
  if (!element) {
    element = document.createElement('meta');
    element.setAttribute(attribute, key);
    document.head.append(element);
  }
  element.content = content;
}

function upsertCanonical(href: string) {
  let element = document.head.querySelector<HTMLLinkElement>('link[rel="canonical"]');
  if (!element) {
    element = document.createElement('link');
    element.rel = 'canonical';
    document.head.append(element);
  }
  element.href = href;
}

export function SeoHead() {
  const { pathname } = useLocation();

  useEffect(() => {
    const page = getSeoPage(pathname);
    const siteUrl = normalizeSiteUrl(
      import.meta.env.VITE_SITE_URL || window.location.origin || DEFAULT_SITE_URL,
    );
    const canonicalUrl = toAbsoluteUrl(siteUrl, page.canonicalPath);
    const socialImageUrl = toAbsoluteUrl(siteUrl, SOCIAL_IMAGE_PATH);

    document.title = page.title;
    upsertCanonical(canonicalUrl);
    upsertMeta('name', 'description', page.description);
    upsertMeta('name', 'robots', 'index, follow, max-image-preview:large');
    upsertMeta('property', 'og:type', 'website');
    upsertMeta('property', 'og:site_name', 'Energy Drip Medellín');
    upsertMeta('property', 'og:locale', 'es_CO');
    upsertMeta('property', 'og:title', page.title);
    upsertMeta('property', 'og:description', page.description);
    upsertMeta('property', 'og:image', socialImageUrl);
    upsertMeta('property', 'og:image:alt', SOCIAL_IMAGE_ALT);
    upsertMeta('property', 'og:url', canonicalUrl);
    upsertMeta('name', 'twitter:card', 'summary_large_image');
    upsertMeta('name', 'twitter:title', page.title);
    upsertMeta('name', 'twitter:description', page.description);
    upsertMeta('name', 'twitter:image', socialImageUrl);
    upsertMeta('name', 'twitter:image:alt', SOCIAL_IMAGE_ALT);
    upsertMeta('name', 'twitter:url', canonicalUrl);

    const existingStructuredData = document.getElementById(JSON_LD_ID);
    if (page.structuredData === 'medical-business') {
      const script = existingStructuredData ?? document.createElement('script');
      script.id = JSON_LD_ID;
      script.setAttribute('type', 'application/ld+json');
      script.textContent = JSON.stringify(createMedicalBusinessStructuredData(siteUrl));
      if (!existingStructuredData) document.head.append(script);
    } else {
      existingStructuredData?.remove();
    }
  }, [pathname]);

  return null;
}
