import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    allowedHosts: [
      'localhost',
      'frontend-polititrack-production.up.railway.app',
      '.railway.app',
    ],
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  preview: {
    port: 3000,
    host: true,
    allowedHosts: [
      'localhost',
      'frontend-polititrack-production.up.railway.app',
      '.railway.app',
    ],
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
})
