import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import tailwindcss from '@tailwindcss/vite';
import { fileURLToPath } from 'node:url';
export default defineConfig({
  base: '/test/', plugins: [svelte(), tailwindcss()],
  resolve: { alias: { '@owlbear-rodeo/sdk': fileURLToPath(new URL('./src/localObr.js', import.meta.url)) } },
  build: { outDir: '../public/test', emptyOutDir: true, rollupOptions: {input: {main:fileURLToPath(new URL('./index.html',import.meta.url)),dice:fileURLToPath(new URL('./dice.html',import.meta.url))}} },
});
