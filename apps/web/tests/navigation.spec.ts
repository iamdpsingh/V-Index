import { test, expect } from '@playwright/test';
import { mockProviders, mockJobsEmpty } from './fixtures/mock-server';

test.beforeEach(async ({ page }) => {
  await mockProviders(page);
  await mockJobsEmpty(page);
  await page.goto('/');
});

test('wordmark is visible and links to /', async ({ page }) => {
  const wordmark = page.getByRole('link', { name: /Rolewisp/ });
  await expect(wordmark).toBeVisible();
  await expect(wordmark).toHaveAttribute('href', '/');
});

test('jobs tab is active by default', async ({ page }) => {
  const jobsBtn = page.getByRole('navigation').getByRole('button', { name: 'Find jobs' });
  await expect(jobsBtn).toHaveAttribute('aria-current', 'page');
});

test('consumer navigation contains Find jobs, For you, and Pricing', async ({ page }) => {
  const nav = page.getByRole('navigation');
  await expect(nav.getByRole('button', { name: 'Find jobs' })).toBeVisible();
  await expect(nav.getByRole('button', { name: 'For you' })).toBeVisible();
  await expect(nav.getByRole('button', { name: 'Pricing' })).toBeVisible();
});

test('clicking pricing tab activates it', async ({ page }) => {
  const nav = page.getByRole('navigation');
  await nav.getByRole('button', { name: 'Pricing' }).click();
  await expect(nav.getByRole('button', { name: 'Pricing' })).toHaveAttribute('aria-current', 'page');
  await expect(nav.getByRole('button', { name: 'Find jobs' })).not.toHaveAttribute('aria-current', 'page');
  await expect(page).toHaveURL(/tab=pricing/);
});

test('clicking for you tab activates it', async ({ page }) => {
  const nav = page.getByRole('navigation');
  await nav.getByRole('button', { name: 'For you' }).click();
  await expect(nav.getByRole('button', { name: 'For you' })).toHaveAttribute('aria-current', 'page');
  await expect(nav.getByRole('button', { name: 'Find jobs' })).not.toHaveAttribute('aria-current', 'page');
  await expect(page).toHaveURL(/tab=for-you/);
});

test('footer reviewer links: clicking coverage shows coverage heading', async ({ page }) => {
  await page.getByRole('button', { name: 'coverage' }).click();
  await expect(page.getByRole('heading', { name: 'Coverage, with evidence.' })).toBeVisible();
  await expect(page).toHaveURL(/tab=coverage/);
});

test('footer operator links: clicking sources shows sources heading', async ({ page }) => {
  await page.getByRole('button', { name: 'sources' }).click();
  await expect(page.getByRole('heading', { name: 'Keep the index current.' })).toBeVisible();
  await expect(page).toHaveURL(/tab=sources/);
});

test('keyboard: Tab key reaches all consumer nav buttons', async ({ page }) => {
  await page.keyboard.press('Tab');
  const nav = page.getByRole('navigation');
  const jobsBtn = nav.getByRole('button', { name: 'Find jobs' });
  const forYouBtn = nav.getByRole('button', { name: 'For you' });
  const pricingBtn = nav.getByRole('button', { name: 'Pricing' });
  for (const btn of [jobsBtn, forYouBtn, pricingBtn]) {
    await expect(btn).toBeVisible();
    await expect(btn).toBeEnabled();
  }
});

test('footer keeps API documentation off the public site', async ({ page }) => {
  await expect(page.getByRole('link', { name: /API documentation/ })).toHaveCount(0);
});
