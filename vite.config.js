import { defineConfig } from 'vite';
export default defineConfig({
  base: './',
  server: {host:'0.0.0.0',port:4173},
  build: {chunkSizeWarningLimit:650, rollupOptions:{input:{main:'index.html',demo:'demo.html'}}}
});
