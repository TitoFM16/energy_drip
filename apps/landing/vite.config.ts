import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5175,
  },
  test: {
    // The landing app is currently static marketing content plus a
    // placeholder /reservar page (the real public booking flow isn't built
    // yet — see "Connected public booking experience" in
    // docs/missing_features.md). There's nothing here worth testing until
    // that lands; passWithNoTests keeps `pnpm test` green in the meantime
    // instead of either failing the build or padding out hollow tests.
    passWithNoTests: true,
  },
});
