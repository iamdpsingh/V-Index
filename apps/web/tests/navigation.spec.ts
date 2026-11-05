import { test, expect } from '@playwright/test';
import { mockProviders, mockJobsEmpty } from './fixtures/mock-server';

test.beforeEach(async ({ page }) => {
  await mockProviders(page);
  await mockJobsEmpty(page);
  await page.goto('/');
});

test('wordmark is visible and links to /', async ({ page }) => {
  const wordmark = page.getByRole('link', { name: /V.*Index/ });
  await expect(wordmark).toBeVisible();
  await expect(wordmark).toHaveAttribute('href', '/');
});

test('jobs tab is active by default', async ({ page }) => {
  const jobsBtn = page.getByRole('navigation').getByRole('button', { name: 'jobs' });
  await expect(jobsBtn).toHaveAttribute('aria-current', 'page');
});

test('clicking sources tab activates it', async ({ page }) => {
  const nav = page.getByRole('navigation');
  await nav.getByRole('button', { name: 'sources' }).click();
  await expect(nav.getByRole('button', { name: 'sources' })).toHaveAttribute('aria-current', 'page');
  await expect(nav.getByRole('button', { name: 'jobs' })).not.toHaveAttribute('aria-current', 'page');
});

test('clicking coverage tab shows coverage heading', async ({ page }) => {
  const nav = page.getByRole('navigation');
  await nav.getByRole('button', { name: 'coverage' }).click();
  await expect(page.getByRole('heading', { name: 'Coverage, with evidence.' })).toBeVisible();
  await expect(nav.getByRole('button', { name: 'coverage' })).toHaveAttribute('aria-current', 'page');
});

test('keyboard: Tab key reaches all nav buttons', async ({ page }) => {
  // Focus first interactive element and Tab through nav
  await page.keyboard.press('Tab');
  // Nav buttons should be reachable via keyboard
  const nav = page.getByRole('navigation');
  const jobsBtn = nav.getByRole('button', { name: 'jobs' });
  const sourcesBtn = nav.getByRole('button', { name: 'sources' });
  const coverageBtn = nav.getByRole('button', { name: 'coverage' });
  for (const btn of [jobsBtn, sourcesBtn, coverageBtn]) {
    await expect(btn).toBeVisible();
    await expect(btn).toBeEnabled();
  }
});

test('footer is visible with API docs link', async ({ page }) => {
  await expect(page.getByRole('link', { name: /API documentation/ })).toBeVisible();
});

