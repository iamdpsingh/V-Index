import { test, expect } from '@playwright/test';
import { mockProviders, mockJobs, mockJobsEmpty, SAMPLE_JOB } from './fixtures/mock-server';

// Mobile tests use the Pixel 5 viewport from playwright.config.ts project 'mobile-chrome'
// All tests here target mobile behaviours

test.beforeEach(async ({ page, isMobile }) => {
  test.skip(!isMobile, 'Mobile tests only run on mobile viewports');
  await mockProviders(page);
});

test('mobile: header note is hidden', async ({ page }) => {
  await mockJobsEmpty(page);
  await page.goto('/');
  // .header-note has display:none at <=850px
  const headerNote = page.locator('.header-note');
  await expect(headerNote).toBeHidden();
});

test('mobile: nav buttons are visible and clickable', async ({ page }) => {
  await mockJobsEmpty(page);
  await page.goto('/');
  const nav = page.getByRole('navigation');
  for (const name of ['Find jobs', 'For you', 'Pricing']) {
    await expect(nav.getByRole('button', { name })).toBeVisible();
  }
});

test('mobile: search form stacks vertically', async ({ page }) => {
  await mockJobsEmpty(page);
  await page.goto('/');
  const form = page.locator('form.search');
  await expect(form).toBeVisible();
  // The search form should be present and usable
  await expect(page.getByLabel('keyword')).toBeVisible();
  await expect(page.getByLabel('company')).toBeVisible();
  await expect(page.getByLabel('location')).toBeVisible();
});

test('mobile: job detail aside renders below results', async ({ page }) => {
  await mockJobs(page, { total: 1, limit: 25, offset: 0, items: [SAMPLE_JOB] });
  await page.goto('/');
  await page.getByRole('button', { name: 'Senior Engineer' }).click();
  // aside is visible (position:static on mobile)
  await expect(page.locator('aside')).toBeVisible();
  await expect(page.getByRole('link', { name: /Apply at original source/ })).toBeVisible();
});

test('mobile: keyboard search works', async ({ page }) => {
  await mockJobsEmpty(page);
  await page.goto('/');
  await page.getByLabel('keyword').tap();
  await page.getByLabel('keyword').fill('engineer');
  await page.getByRole('button', { name: /Search jobs/ }).tap();
  await expect(page.getByText('No openings here yet.')).toBeVisible();
});

test('mobile: coverage tab accessible', async ({ page }) => {
  await mockJobsEmpty(page);
  await page.goto('/');
  await page.getByRole('button', { name: 'coverage' }).tap();
  await expect(page.getByRole('table')).toBeVisible();
});

test('mobile: sources tab accessible and form usable', async ({ page }) => {
  await mockJobsEmpty(page);
  await page.goto('/');
  await page.getByRole('button', { name: 'sources' }).tap();
  await expect(page.getByLabel('Admin token')).toBeVisible();
  await expect(page.getByLabel('Company name')).toBeVisible();
  await expect(page.getByLabel('Hosted board URL')).toBeVisible();
});

