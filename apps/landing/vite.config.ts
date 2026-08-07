import { access, mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { loadEnv, type Plugin } from 'vite';
// vitest/config re-exports vite's defineConfig with the `test` field typed
// in — plain `vite`'s UserConfig doesn't know about it.
import { defineConfig } from 'vitest/config';
import {
  createMedicalBusinessStructuredData,
  DEFAULT_SITE_URL,
  type SeoPage,
  SEO_PAGES,
  SOCIAL_IMAGE_ALT,
  SOCIAL_IMAGE_PATH,
  toAbsoluteUrl,
} from './src/seo/metadata.ts';

const LANDING_ROOT = dirname(fileURLToPath(import.meta.url));
const SEO_PLACEHOLDER = '<!-- seo:head -->';
const SEO_BLOCK_PATTERN = /<!-- seo:begin -->[\s\S]*?<!-- seo:end -->/;

function escapeHtml(value: string): string {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

function renderSeoHead(page: SeoPage, siteUrl: string): string {
  const title = escapeHtml(page.title);
  const description = escapeHtml(page.description);
  const canonicalUrl = escapeHtml(toAbsoluteUrl(siteUrl, page.canonicalPath));
  const socialImageUrl = escapeHtml(toAbsoluteUrl(siteUrl, SOCIAL_IMAGE_PATH));
  const socialImageAlt = escapeHtml(SOCIAL_IMAGE_ALT);
  const structuredData =
    page.structuredData === 'medical-business'
      ? `\n    <script id="energy-drip-medical-business-jsonld" type="application/ld+json">${JSON.stringify(createMedicalBusinessStructuredData(siteUrl)).replaceAll('<', '\\u003c')}</script>`
      : '';

  return `<!-- seo:begin -->
    <title>${title}</title>
    <meta name="description" content="${description}" />
    <meta name="robots" content="index, follow, max-image-preview:large" />
    <link rel="canonical" href="${canonicalUrl}" />
    <meta property="og:type" content="website" />
    <meta property="og:site_name" content="Energy Drip Medellín" />
    <meta property="og:locale" content="es_CO" />
    <meta property="og:title" content="${title}" />
    <meta property="og:description" content="${description}" />
    <meta property="og:image" content="${socialImageUrl}" />
    <meta property="og:image:alt" content="${socialImageAlt}" />
    <meta property="og:url" content="${canonicalUrl}" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="${title}" />
    <meta name="twitter:description" content="${description}" />
    <meta name="twitter:image" content="${socialImageUrl}" />
    <meta name="twitter:image:alt" content="${socialImageAlt}" />
    <meta name="twitter:url" content="${canonicalUrl}" />${structuredData}
    <!-- seo:end -->`;
}

function renderSitemap(siteUrl: string): string {
  const urls = SEO_PAGES.map(
    (page) =>
      `  <url>\n    <loc>${escapeHtml(toAbsoluteUrl(siteUrl, page.canonicalPath))}</loc>\n  </url>`,
  ).join('\n');

  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>
`;
}

function renderRobots(siteUrl: string): string {
  return `User-agent: *
Allow: /

Sitemap: ${toAbsoluteUrl(siteUrl, '/sitemap.xml')}
`;
}

function routeOutputPath(distDirectory: string, page: SeoPage): string {
  if (page.path === '/') return resolve(distDirectory, 'index.html');
  return resolve(distDirectory, page.path.slice(1), 'index.html');
}

function assertOutput(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(`[landing-seo] ${message}`);
}

async function verifySeoOutput(distDirectory: string, siteUrl: string) {
  for (const page of SEO_PAGES) {
    const outputPath = routeOutputPath(distDirectory, page);
    const html = await readFile(outputPath, 'utf8');
    const canonicalUrl = toAbsoluteUrl(siteUrl, page.canonicalPath);
    const socialImageUrl = toAbsoluteUrl(siteUrl, SOCIAL_IMAGE_PATH);

    assertOutput(
      html.includes(`<title>${escapeHtml(page.title)}</title>`),
      `${page.path} is missing its title`,
    );
    assertOutput(
      html.includes(`<meta name="description" content="${escapeHtml(page.description)}" />`),
      `${page.path} is missing its description`,
    );
    assertOutput(
      html.includes(`<link rel="canonical" href="${escapeHtml(canonicalUrl)}" />`),
      `${page.path} is missing its canonical URL`,
    );
    assertOutput(
      html.includes(`content="${escapeHtml(socialImageUrl)}"`),
      `${page.path} is missing its social image`,
    );
    assertOutput(
      !html.includes(SEO_PLACEHOLDER),
      `${page.path} still contains the SEO placeholder`,
    );

    const hasStructuredData = html.includes('energy-drip-medical-business-jsonld');
    assertOutput(
      hasStructuredData === (page.structuredData === 'medical-business'),
      `${page.path} has an unexpected structured-data state`,
    );
  }

  const sitemap = await readFile(resolve(distDirectory, 'sitemap.xml'), 'utf8');
  assertOutput(
    sitemap.startsWith('<?xml version="1.0" encoding="UTF-8"?>'),
    'sitemap.xml has no XML declaration',
  );
  assertOutput(
    sitemap.includes('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'),
    'sitemap.xml has no sitemap namespace',
  );
  assertOutput(
    (sitemap.match(/<url>/g) ?? []).length === SEO_PAGES.length,
    'sitemap.xml route count is incorrect',
  );
  for (const page of SEO_PAGES) {
    assertOutput(
      sitemap.includes(`<loc>${escapeHtml(toAbsoluteUrl(siteUrl, page.canonicalPath))}</loc>`),
      `sitemap.xml is missing ${page.path}`,
    );
  }
  assertOutput(sitemap.trimEnd().endsWith('</urlset>'), 'sitemap.xml is not closed');

  const robots = await readFile(resolve(distDirectory, 'robots.txt'), 'utf8');
  assertOutput(/^User-agent: \*$/m.test(robots), 'robots.txt has no user-agent policy');
  assertOutput(/^Allow: \/$/m.test(robots), 'robots.txt does not allow the public site');
  assertOutput(
    robots.includes(`Sitemap: ${toAbsoluteUrl(siteUrl, '/sitemap.xml')}`),
    'robots.txt has no sitemap URL',
  );
  await access(resolve(distDirectory, SOCIAL_IMAGE_PATH.slice(1)));
}

function landingSeoPlugin(siteUrl: string): Plugin {
  const distDirectory = resolve(LANDING_ROOT, 'dist');

  return {
    name: 'landing-technical-seo',
    transformIndexHtml(html) {
      return html.replace(SEO_PLACEHOLDER, renderSeoHead(SEO_PAGES[0], siteUrl));
    },
    async closeBundle() {
      const homePath = routeOutputPath(distDirectory, SEO_PAGES[0]);
      const homeHtml = await readFile(homePath, 'utf8');

      for (const page of SEO_PAGES.slice(1)) {
        const outputPath = routeOutputPath(distDirectory, page);
        await mkdir(dirname(outputPath), { recursive: true });
        await writeFile(
          outputPath,
          homeHtml.replace(SEO_BLOCK_PATTERN, renderSeoHead(page, siteUrl)),
        );
      }

      await writeFile(resolve(distDirectory, 'sitemap.xml'), renderSitemap(siteUrl));
      await writeFile(resolve(distDirectory, 'robots.txt'), renderRobots(siteUrl));
      await verifySeoOutput(distDirectory, siteUrl);
    },
  };
}

export default defineConfig(({ mode }) => {
  const environment = loadEnv(mode, LANDING_ROOT, '');
  const siteUrl = environment.VITE_SITE_URL || DEFAULT_SITE_URL;

  if (!environment.VITE_SITE_URL) {
    console.warn(
      `[landing-seo] VITE_SITE_URL is not set; canonical and sitemap URLs will use ${DEFAULT_SITE_URL}. Set the public origin in production.`,
    );
  }

  return {
    plugins: [react(), tailwindcss(), landingSeoPlugin(siteUrl)],
    server: {
      port: 5175,
    },
    test: {
      // Most of the landing app is still static marketing content with no
      // logic worth testing — passWithNoTests keeps `pnpm test` green for
      // that. The /reservar booking form's non-trivial logic (payload
      // shaping) is covered directly; there's no DOM testing stack
      // (jsdom/testing-library) here, so form interaction itself isn't
      // covered — see "Connected public booking experience" in
      // docs/missing_features.md.
      passWithNoTests: true,
    },
  };
});
