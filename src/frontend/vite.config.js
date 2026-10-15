import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { viteSingleFile } from 'vite-plugin-singlefile';

// `npm run build:standalone` produces one self-contained HTML file that opens from disk (file://).
export default defineConfig(({ mode }) => {
  const standalone = mode === 'standalone';
  return {
    base: standalone ? './' : '/',
    plugins: [react(), ...(standalone ? [viteSingleFile()] : [])],
    server: {
      port: 5173,
      proxy: {
        '/api': 'http://localhost:8000',
        '/docs': 'http://localhost:8000',
        '/redoc': 'http://localhost:8000',
        '/openapi.json': 'http://localhost:8000',
      },
    },
  };
});
