import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Vite 설정 (순수 JSX + React, TypeScript/Tailwind 미사용)
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: 'localhost',
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
});
