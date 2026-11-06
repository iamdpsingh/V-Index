import { test, expect } from '@playwright/test';
import {
  mockProviders, mockJobsEmpty, mockSources,
  mockSourceError, mockRefreshError, SAMPLE_SOURCE_OUT, SAMPLE_RUN_OUT,
} from './fixtures/mock-server';

async function goToSources(page: Parameters<typeof mockProviders>[0]) {
  await mockProviders(page);
  await mockJobsEmpty(page);
  await page.goto('/');
  await page.getByRole('button', { name: 'sources' }).click();
}

test('admin token input is password type', async ({ page }) => {
  await goToSources(page);
  const tokenInput = page.getByLabel('Admin token');
  await expect(tokenInput).toHaveAttribute('type', 'password');
});

test('admin token is not persisted to localStorage', async ({ page }) => {
  await goToSources(page);
  await page.getByLabel('Admin token').fill('secret-token');
  // Reload page — token should be gone
  await page.reload();
  await page.getByRole('button', { name: 'sources' }).click();
  await expect(page.getByLabel('Admin token')).toHaveValue('');
});

test('Add source button disabled without token', async ({ page }) => {
  await goToSources(page);
  await expect(page.getByRole('button', { name: /Add source/ })).toBeDisabled();
});

test('Reload source status button disabled without token', async ({ page }) => {
  await goToSources(page);
  await expect(page.getByRole('button', { name: /Reload source status/ })).toBeDisabled();
});

test('refresh_minutes field present with min 60 max 10080', async ({ page }) => {
  await goToSources(page);
  const input = page.getByLabel('Refresh interval (minutes)');
  await expect(input).toBeVisible();
  await expect(input).toHaveAttribute('min', '60');
  await expect(input).toHaveAttribute('max', '10080');
});

test('successfully adding a source shows confirmation', async ({ page }) => {
  await mockSources(page);
  await goToSources(page);
  await page.getByLabel('Admin token').fill('valid-token');
  await page.getByLabel('Company name').fill('Acme Corp');
  await page.getByLabel('Hosted board URL').fill('https://boards.greenhouse.io/acme');
  await page.getByRole('button', { name: /Add source/ }).click();
  await expect(page.getByRole('status')).toContainText('Source added');
});

test('401 error shows "Invalid token"', async ({ page }) => {
  await mockSourceError(page, 401, 'Unauthorized');
  await goToSources(page);
  await page.getByLabel('Admin token').fill('wrong-token');
  await page.getByLabel('Company name').fill('Acme Corp');
  await page.getByLabel('Hosted board URL').fill('https://boards.greenhouse.io/acme');
  await page.getByRole('button', { name: /Add source/ }).click();
  await expect(page.locator('.notice.error')).toContainText('Invalid token');
});

test('409 error shows "Source already exists"', async ({ page }) => {
  await mockSourceError(page, 409, 'Source already registered');
  await goToSources(page);
  await page.getByLabel('Admin token').fill('valid-token');
  await page.getByLabel('Company name').fill('Acme Corp');
  await page.getByLabel('Hosted board URL').fill('https://boards.greenhouse.io/acme');
  await page.getByRole('button', { name: /Add source/ }).click();
  await expect(page.locator('.notice.error')).toContainText('Source already exists');
});

test('503 error shows "Service unavailable" message', async ({ page }) => {
  await mockSourceError(page, 503, 'Service Unavailable');
  await goToSources(page);
  await page.getByLabel('Admin token').fill('valid-token');
  await page.getByLabel('Company name').fill('Acme Corp');
  await page.getByLabel('Hosted board URL').fill('https://boards.greenhouse.io/acme');
  await page.getByRole('button', { name: /Add source/ }).click();
  await expect(page.locator('.notice.error')).toContainText('Service unavailable');
});

test('connected sources list shows after loading', async ({ page }) => {
  await mockSources(page);
  await goToSources(page);
  await page.getByLabel('Admin token').fill('valid-token');
  await page.getByRole('button', { name: /Reload source status/ }).click();
  await expect(page.getByText('Acme Corp')).toBeVisible();
  await expect(page.locator('.job-card .pill', { hasText: /greenhouse/i })).toBeVisible();
});

test('runs table shows finished_at column', async ({ page }) => {
  await mockSources(page, [SAMPLE_SOURCE_OUT], [SAMPLE_RUN_OUT]);
  await goToSources(page);
  await page.getByLabel('Admin token').fill('valid-token');
  await page.getByRole('button', { name: /Reload source status/ }).click();
  await expect(page.getByRole('columnheader', { name: 'Finished' })).toBeVisible();
});

test('no token means sources shows empty prompt', async ({ page }) => {
  await goToSources(page);
  await expect(page.getByText('Enter your admin token and load source status.')).toBeVisible();
});

