import { test, expect } from '@playwright/test';
import { mockProviders, mockJobsEmpty, SAMPLE_PROVIDERS } from './fixtures/mock-server';

test.beforeEach(async ({ page }) => {
  await mockProviders(page, SAMPLE_PROVIDERS);
  await mockJobsEmpty(page);
  await page.goto('/');
  await page.getByRole('button', { name: 'coverage' }).click();
});

test('coverage table is visible', async ({ page }) => {
  await expect(page.getByRole('table')).toBeVisible();
  await expect(page.getByText('Required ATS and job-board platforms')).toBeVisible();
});

test('shows all providers including unimplemented', async ({ page }) => {
  // All 5 providers in SAMPLE_PROVIDERS should appear
  for (const p of SAMPLE_PROVIDERS) {
    await expect(page.getByRole('rowheader', { name: new RegExp(p.name) })).toBeVisible();
  }
});

test('summary notice distinguishes implemented from live-verified', async ({ page }) => {
  // 3 implemented (Greenhouse, Lever, Ashby), 2 live-verified, 2 not-started
  await expect(page.getByText(/3 connectors implemented/)).toBeVisible();
  await expect(page.getByText(/2 have live evidence/)).toBeVisible();
  await expect(page.getByText(/2 remain unimplemented/)).toBeVisible();
});

test('live-verified providers have green pill', async ({ page }) => {
  // Greenhouse and Lever are LIVE_VERIFIED
  const rows = page.getByRole('row');
  const greenhouse = rows.filter({ hasText: 'Greenhouse' });
  await expect(greenhouse.locator('.pill.good')).toBeVisible();
});

test('unimplemented providers show not started status', async ({ page }) => {
  const rows = page.getByRole('row');
  const workday = rows.filter({ hasText: 'Workday' });
  await expect(workday).toContainText('not started');
});

test('limitations are displayed for unimplemented providers', async ({ page }) => {
  await expect(page.getByText('Tenant-specific URLs')).toBeVisible();
});

test('failure_reason is shown for providers that have it', async ({ page }) => {
  await expect(page.getByText('Requires API key')).toBeVisible();
});

test('extraction count shows dash for unimplemented', async ({ page }) => {
  const rows = page.getByRole('row');
  const workday = rows.filter({ hasText: 'Workday' });
  await expect(workday).toContainText('—');
});

test('index-note shows live-checked count not implemented count', async ({ page }) => {
  // Should say "2 / 5 platforms live-checked" (2 LIVE_VERIFIED out of 5 total)
  await expect(page.locator('.index-note')).toContainText('2 / 5 platforms live-checked');
});

