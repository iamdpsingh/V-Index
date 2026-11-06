import { test, expect } from '@playwright/test';
import { mockJobsEmpty, mockProviders } from './fixtures/mock-server';

test.beforeEach(async ({ page }) => {
  await mockProviders(page);
  await mockJobsEmpty(page);
  await page.goto('/');
});

test('Rolewisp brand wordmark is visible with open-corner mark', async ({ page }) => {
  const wordmark = page.locator('a.wordmark');
  await expect(wordmark).toBeVisible();
  await expect(wordmark.locator('.brand-name')).toHaveText('Rolewisp');
  await expect(wordmark.locator('svg')).toBeVisible();
});

test('tagline "Find your next opening." is present in header and intro', async ({ page }) => {
  // Check header note
  const headerNote = page.locator('.header-note');
  await expect(headerNote).toHaveText('Find your next opening.');

  // Check main heading
  const h1 = page.getByRole('heading', { level: 1 });
  await expect(h1).toHaveText('Find your next opening.');
});

test('footer retains repository attribution to V-Index', async ({ page }) => {
  const footer = page.locator('footer');
  await expect(footer).toContainText('Rolewisp — built in the V—Index repository');
  await expect(footer).toContainText('Original sources. Visible evidence.');
});

