import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { viteSingleFile } from 'vite-plugin-singlefile';

// `npm run build:standalone` produces one self-contained HTML file that opens from disk (file://).
export default defineConfig(({ mode }) => {
  const standalone = mode === 'standalone';
  return {
    base: standalone ? './' : '/',
    plugins: [react(), ...(standalone ? [viteSingleFile()] : [])],
    server: { port: 5173 },
  };
});
