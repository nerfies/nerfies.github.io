// @ts-check
import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import react from '@astrojs/react';

// Deployed at https://tsglab.github.io/mechinterp-safety/ (GitHub Pages project site).
// CI sets SITE_BASE from the repository name. Override with SITE_BASE=/ for previews at the domain root.
export default defineConfig({
  site: 'https://tsglab.github.io',
  base: process.env.SITE_BASE ?? '/mechinterp-safety',
  trailingSlash: 'always',
  integrations: [mdx(), react()],
  build: { format: 'directory' },
});
