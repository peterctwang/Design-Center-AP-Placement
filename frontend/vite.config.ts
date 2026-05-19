import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// Build output goes directly into backend/static so the FastAPI app
// can serve the SPA without any extra step.
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: path.resolve(__dirname, '../backend/static'),
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': { target: 'ws://localhost:8000', ws: true },
      '/uploads': 'http://localhost:8000',
    },
  },
});
