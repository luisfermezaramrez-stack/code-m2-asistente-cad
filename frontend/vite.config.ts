import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

// Solo desarrollo/preview: no se incorpora ninguna URL del backend al bundle.
const proxy = Object.fromEntries(
  ['/generar', '/generaciones', '/health'].map((route) => [route, 'http://127.0.0.1:8000']),
)

export default defineConfig({
  plugins: [vue()],
  server: { proxy, fs: { allow: ['..'] } },
  preview: { proxy },
  test: { environment: 'jsdom', restoreMocks: true, include: ['tests/**/*.test.ts'] },
})
