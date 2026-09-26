import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  use: {baseURL: 'http://127.0.0.1:8765', browserName: 'chromium'},
  webServer: {
    command: '.venv/bin/python -m uvicorn app.asgi:app --host 127.0.0.1 --port 8765',
    cwd: '..',
    url: 'http://127.0.0.1:8765/api/v1/studio/bootstrap',
    reuseExistingServer: !process.env.CI,
  },
});
