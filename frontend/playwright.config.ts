import { defineConfig, devices } from '@playwright/test'

// E2E de la SPA (SPEC-042 / HU-41). Se prueba el build real que sirve FastAPI con
// `vite preview`, y el backend se simula con `page.route` sobre `/v1`: sin red
// externa, sin API key y sin GPU (RNF-1). Un solo navegador (RF-5, Supuesto).
const puerto = 4173
const url = `http://127.0.0.1:${puerto}`

export default defineConfig({
  testDir: './e2e',
  // Nunca en `npm test`: Vitest sigue siendo la suite de componentes (RNF-3).
  // Un solo worker: los escenarios comparten el servidor de preview y el orden
  // no debe depender de la concurrencia (RNF-2).
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: 0,
  timeout: 30_000,
  expect: { timeout: 10_000 },
  outputDir: 'test-results',
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report' }]],
  use: {
    baseURL: url,
    // AC2: el fallo deja captura y traza junto al reporte HTML, que CI publica.
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    // El build lo produce `make e2e` antes de invocar la suite.
    command: `npm run preview -- --port ${puerto} --strictPort`,
    url,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
})
