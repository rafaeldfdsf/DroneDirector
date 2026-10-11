import { defineConfig } from '@playwright/test';
import { resolve } from 'node:path';

process.env['PLAYWRIGHT_BROWSERS_PATH'] ??= resolve('../work/browsers');

export default defineConfig({
  testDir: './tests',
  timeout: 120_000,
  workers: 1,
  use: { baseURL: 'http://localhost:4200', browserName: 'chromium', trace: 'retain-on-failure' },
  outputDir: '../work/playwright-results',
  webServer: [
    {
      command:
        '..\\backend\\.venv\\Scripts\\python.exe -m uvicorn main:app --app-dir ../backend --host 127.0.0.1 --port 8000',
      url: 'http://localhost:8000/api/health',
      reuseExistingServer: true,
      timeout: 30000,
      env: { DRONE_PROJECTS_DIR: resolve('../work/ui-projects') },
    },
    {
      command: 'npm start -- --host 127.0.0.1',
      url: 'http://localhost:4200',
      reuseExistingServer: true,
      timeout: 60000,
    },
  ],
});
