import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
// vitest/config re-exports vite's defineConfig with the `test` field typed
// in — plain `vite`'s UserConfig doesn't know about it.
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react(), tailwindcss()],
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
});
