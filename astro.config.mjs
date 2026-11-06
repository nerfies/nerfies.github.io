// @ts-check
import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import react from '@astrojs/react';

// Deployed at https://tsglab.github.io/mi_survey/ (GitHub Pages project site).
// Override with SITE_BASE=/ for local previews at the domain root if needed.
export default defineConfig({
  site: 'https://tsglab.github.io',
  base: process.env.SITE_BASE ?? '/mi_survey',
  trailingSlash: 'always',
  integrations: [mdx(), react()],
  build: { format: 'directory' },
});
