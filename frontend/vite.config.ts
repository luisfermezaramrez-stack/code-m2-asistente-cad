import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

// Solo desarrollo/preview: no se incorpora ninguna URL del backend al bundle.
// La SPA consume exclusivamente /v1; las rutas planas son redirecciones temporales.
const proxy = { '/v1': 'http://127.0.0.1:8000' }

export default defineConfig({
  plugins: [vue()],
  server: { proxy, fs: { allow: ['..'] } },
  preview: { proxy },
  test: { environment: 'jsdom', restoreMocks: true, include: ['tests/**/*.test.ts'] },
})
