import { test, expect } from '@playwright/test';
import {
  mockProviders,
  mockJobs,
  mockJobsEmpty,
  SAMPLE_JOB,
  SAMPLE_PROVIDERS,
} from './fixtures/mock-server';

test.beforeEach(async ({ page }) => {
  await mockProviders(page, SAMPLE_PROVIDERS);
  await mockJobs(page, {
    total: 1,
    limit: 25,
    offset: 0,
    items: [SAMPLE_JOB],
  });
});

test('URL state: search submission updates window query params', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('keyword').fill('staff');
  await page.getByRole('button', { name: /Search jobs/ }).click();

  await expect(page).toHaveURL(/keyword=staff/);
});

test('URL state: switching tab updates window query param', async ({ page }) => {
  await page.goto('/');
  const nav = page.getByRole('navigation');
  await nav.getByRole('button', { name: 'coverage' }).click();

  await expect(page).toHaveURL(/tab=coverage/);
  await expect(page.getByRole('heading', { name: 'Coverage, with evidence.' })).toBeVisible();
});

test('URL state: direct load with ?tab=coverage opens coverage tab directly', async ({ page }) => {
  await page.goto('/?tab=coverage');
  await expect(page.getByRole('heading', { name: 'Coverage, with evidence.' })).toBeVisible();
  const nav = page.getByRole('navigation');
  await expect(nav.getByRole('button', { name: 'coverage' })).toHaveAttribute('aria-current', 'page');
});

test('Job record: index reference number (№ 0001) is displayed', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('.ref-number')).toContainText('№ 0001');
});

test('Coverage controls: platform kind filters narrow the table', async ({ page }) => {
  await page.goto('/?tab=coverage');
  await expect(page.getByRole('table')).toBeVisible();

  // Click ATS filter
  await page.getByRole('button', { name: /ATS \(/ }).click();
  // Table should show Greenhouse and Lever
  await expect(page.getByRole('rowheader', { name: /Greenhouse/ })).toBeVisible();
});

test('Coverage controls: search input filters platform table', async ({ page }) => {
  await page.goto('/?tab=coverage');
  await page.getByPlaceholder('Filter platform or limitation…').fill('Workday');

  // Workday should be visible
  await expect(page.getByRole('rowheader', { name: /Workday/ })).toBeVisible();
  // Greenhouse should be filtered out
  await expect(page.getByRole('rowheader', { name: /Greenhouse/ })).toHaveCount(0);
});

test('Mobile detail: return button clears selection and restores result view', async ({
  page,
  isMobile,
}) => {
  test.skip(!isMobile, 'Mobile-only flow test');
  await page.goto('/');

  // Select job
  await page.getByRole('button', { name: 'Senior Engineer' }).click();
  await expect(page.locator('.mobile-back-btn')).toBeVisible();

  // Click return
  await page.locator('.mobile-back-btn').click();
  await expect(page.getByRole('button', { name: 'Senior Engineer' })).toBeVisible();
});

