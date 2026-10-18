import { test, expect, type Page } from '@playwright/test';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const evidenceDirectory = process.env.CIVIC_QA_DIR || join(tmpdir(), 'civicshield-qa');

const photo = { name: 'synthetic-workflow-evidence.png', mimeType: 'image/png', buffer: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=', 'base64') };

async function login(page: Page, role: string) {
  await page.goto('/');
  const signout = page.getByRole('button', { name: 'Sign out', exact: true });
  await expect(signout.or(page.getByRole('button', { name: 'Sign in', exact: true }))).toBeVisible();
  if (await signout.isVisible()) await signout.click();
  await page.getByRole('button', { name: role, exact: true }).click();
  await expect(page.locator('main')).toBeVisible();
}

async function open(page: Page, reference: string) {
  await page.goto('/incidents');
  await page.getByLabel('Search incidents').fill(reference);
  await page.getByRole('row').filter({ hasText: reference }).getByRole('button').first().click();
  await expect(page.getByRole('dialog').first()).toBeVisible();
}

test('photo-only report → location-only direct assignment → optional-note completion → correction → verified closure', async ({ page, request }) => {
  test.setTimeout(180_000);
  page.setDefaultTimeout(15000);
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.context().setGeolocation({ latitude: 31.5114, longitude: 74.3506 });
  await page.context().grantPermissions(['geolocation']);
  await login(page, 'Citizen');
  const chooser = page.waitForEvent('filechooser', { timeout: 15000 });
  await page.getByRole('button', { name: 'Upload a photo', exact: true }).click();
  await (await chooser).setFiles(photo);
  await expect(page.getByText('Photo detection is unavailable', { exact: true })).toBeVisible();
  await expect(page.getByLabel('Description (optional)', { exact: true })).toHaveValue('');
  await expect(page.getByLabel('Report title (optional)', { exact: true })).toHaveValue('');
  await page.getByLabel('Issue category', { exact: true }).selectOption('Blocked drainage');
  await expect(page.locator('.location-feedback.confirmed')).toBeVisible();
  const result = page.waitForResponse(r => r.url().endsWith('/api/reports') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Submit report', exact: true }).click();
  const created = await (await result).json();
  expect(created.description).toBe('');
  expect(created.analysis.image_analyzed).toBe(false);
  const reference = created.reference;
  await page.getByRole('button', { name: 'Close dialog', exact: true }).click();
  await login(page, 'Authority');
  await open(page, reference);
  await page.getByRole('tab', { name: 'Response', exact: true }).click();
  const token = await page.evaluate(() => localStorage.getItem('civicshield.session.v1'));
  const workers = await (await request.get('/api/workers', { headers: { Authorization: `Bearer ${token}` } })).json();
  const workerLogin = await (await request.post('/api/auth/login', { data: { email: 'worker@civicshield.demo', password: 'CivicDemo!2026' } })).json();
  const worker = workers.find((w: any) => w.id === workerLogin.user.id);
  expect(worker).toBeTruthy();
  await page.getByLabel('Choose a worker (optional)', { exact: true }).selectOption(String(worker.id));
  await page.getByRole('radio', { name: /Share location only/ }).check();
  await page.getByLabel('Assignment instructions', { exact: true }).fill('Clear the blocked drain at the shared point. Synthetic acceptance test.');
  await page.getByRole('button', { name: 'Assign worker', exact: true }).click();
  await expect(page.getByText('Response team assigned', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Close dialog', exact: true }).click();
  await login(page, 'Worker');
  await open(page, reference);
  await expect(page.getByRole('heading', { name: 'Location-only task', exact: true })).toBeVisible();
  await expect(page.locator('.report-photo-evidence img')).toHaveCount(0);
  const workerToken = await page.evaluate(() => localStorage.getItem('civicshield.session.v1'));
  const read = await request.get(`/api/incidents/${created.id}`, { headers: { Authorization: `Bearer ${workerToken}` } });
  expect((await read.json()).description).toBe('');
  const original = await request.get(`/api/uploads/${created.attachments[0].id}/file`, { headers: { Authorization: `Bearer ${workerToken}` } });
  expect(original.status()).toBe(403);
  for (let cycle = 0; cycle < 2; cycle++) {
    await page.getByRole('tab', { name: 'Response', exact: true }).click();
    await page.getByLabel('Completion evidence', { exact: true }).setInputFiles(photo);
    await expect(page.getByLabel('Completion notes (optional)', { exact: true })).toHaveValue('');
    await page.getByRole('button', { name: 'Submit completion', exact: true }).click();
    await expect(page.getByText('Completion submitted for authority verification', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Close dialog', exact: true }).click();
    await login(page, 'Authority');
    await open(page, reference);
    await page.getByRole('tab', { name: 'Response', exact: true }).click();
    await expect(page.locator('.completion-review-panel .evidence img').first()).toBeVisible();
    await page.getByLabel('Verification decision', { exact: true }).fill(cycle ? 'Fresh completion photograph verified. Repair approved.' : 'Clear the remaining obstruction and send a fresh photograph.');
    await page.getByRole('button', { name: cycle ? 'Approve repair & close' : 'Return for more work', exact: true }).click();
    await expect(page.locator(`.incident-detail .detail-title .badge[title="${cycle ? 'Closed' : 'In Progress'}"]`)).toBeVisible();
    await page.getByRole('button', { name: 'Close dialog', exact: true }).click();
    if (!cycle) { await login(page, 'Worker'); await open(page, reference); }
  }
  await login(page, 'Citizen');
  await open(page, reference);
  await expect(page.locator('.incident-detail .detail-title .badge-closed')).toContainText('Closed');
  await page.screenshot({ path: join(evidenceDirectory, 'verified-photo-workflow.png') });
  expect(errors).toEqual([]);
});

for (const width of [1440, 390]) {
  test(`citizen weather and readable alerts show real API data at ${width}px`, async ({ page, request }) => {
    await page.setViewportSize({ width, height: 1000 });
    await login(page, 'Citizen');
    const token = await page.evaluate(() => localStorage.getItem('civicshield.session.v1'));
    const actual = await (await request.get('/api/citizen/weather?latitude=31.5204&longitude=74.3587', { headers: { Authorization: `Bearer ${token}` } })).json();
    expect(actual.available, 'Live weather must succeed for this acceptance check').toBe(true);
    expect(actual.synthetic).toBe(false);
    await page.goto('/weather');
    await expect(page.locator('.forecast-day')).toHaveCount(7);
    await expect(page.locator('.weather-provenance')).toContainText('Open-Meteo');
    await expect(page.locator('.weather-measures')).toContainText('Humidity');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    await page.screenshot({ path: join(evidenceDirectory, `weather-${width}.png`), fullPage: true });
    await page.goto('/alerts');
    await expect(page.locator('.alerts-source-notice')).toContainText('No official warning feed');
    await expect(page.locator('.citizen-risk-card').first()).toContainText('Flooding / waterlogging');
    await expect(page.locator('.citizen-risk-card').first()).toContainText('What you can do');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    await page.screenshot({ path: join(evidenceDirectory, `alerts-${width}.png`), fullPage: true });
  });
}

test('weather outage is explicit and GPS denial leaves no invented report coordinates', async ({ page }) => {
  await login(page, 'Citizen');
  await page.route('**/api/citizen/weather?*', route => route.fulfill({ json: { available: false, current: null, daily: [], message: 'Weather service temporarily unavailable.' } }));
  await page.goto('/weather');
  await expect(page.getByRole('heading', { name: 'Weather is unavailable right now' })).toBeVisible();
  await expect(page.locator('.forecast-day')).toHaveCount(0);
  await page.getByRole('button', { name: 'New report', exact: true }).click();
  await expect(page.locator('.location-feedback')).toContainText('Location permission is unavailable', { timeout: 15000 });
  await page.getByText('Enter coordinates manually', { exact: true }).click();
  await expect(page.getByLabel('Latitude', { exact: true })).toHaveValue('');
  await expect(page.getByLabel('Longitude', { exact: true })).toHaveValue('');
  await page.getByLabel('Description (optional)', { exact: true }).fill('Blocked drain with standing water near the public crossing.');
  await page.getByRole('button', { name: 'Submit report', exact: true }).click();
  await expect(page.getByRole('alert').filter({ hasText: 'Choose the problem' })).toBeVisible();
});
