import { describe, expect, it } from 'vitest';
import {
  createMedicalBusinessStructuredData,
  getSeoPage,
  SEO_PAGES,
  toAbsoluteUrl,
} from './metadata';

describe('landing SEO metadata', () => {
  it('defines unique metadata for every public route', () => {
    expect(SEO_PAGES).toHaveLength(10);
    expect(new Set(SEO_PAGES.map((page) => page.path)).size).toBe(SEO_PAGES.length);
    expect(new Set(SEO_PAGES.map((page) => page.title)).size).toBe(SEO_PAGES.length);
    expect(SEO_PAGES.every((page) => page.description.length > 50)).toBe(true);
  });

  it('normalizes trailing slashes when resolving a route', () => {
    expect(getSeoPage('/servicios/').path).toBe('/servicios');
    expect(toAbsoluteUrl('https://example.test/', '/servicios/')).toBe(
      'https://example.test/servicios/',
    );
  });

  it('uses only known Medellín service facts in the home structured data', () => {
    const data = createMedicalBusinessStructuredData('https://example.test');
    expect(data.name).toBe('Energy Drip Medellín');
    expect(data.address).toEqual({
      '@type': 'PostalAddress',
      addressLocality: 'Medellín',
      addressCountry: 'CO',
    });
    expect(data.serviceType).toContain('Terapias IV móviles');
    expect(data).not.toHaveProperty('telephone');
    expect(data).not.toHaveProperty('streetAddress');
  });
});
