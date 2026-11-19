import { test, expect } from '@playwright/test';
import { mockJobsEmpty, mockProviders } from './fixtures/mock-server';

test.beforeEach(async ({ page }) => {
  await mockProviders(page);
  await mockJobsEmpty(page);
  await page.goto('/');
});

test('Rolewisp brand wordmark is visible with continuous ribbon R mark', async ({ page }) => {
  const wordmark = page.locator('a.wordmark');
  await expect(wordmark).toBeVisible();
  await expect(wordmark.locator('.brand-name')).toHaveText('Rolewisp');
  const svg = wordmark.locator('svg');
  await expect(svg).toBeVisible();
  // Verify ribbon R mark geometry from design/rolewisp/logo-symbol.svg
  await expect(svg.locator('path')).toHaveAttribute(
    'd',
    'M10 39V16C10 9 16 5 23 5C31 5 37 10 37 17C37 24 31 29 23 29H20L36 43'
  );
});

test('tagline "Find your next opening." is the search heading', async ({ page }) => {
  // Check main heading
  const h1 = page.getByRole('heading', { level: 1 });
  await expect(h1).toHaveText('Find your next opening.');
});

test('footer links privacy policies and keeps repository details out of the product', async ({ page }) => {
  const footer = page.locator('footer');
  await expect(footer).toContainText('Rolewisp');
  await expect(footer).not.toContainText('V-Index');
  for (const name of ['Privacy', 'Cookies', 'Terms', 'Refunds']) {
    await expect(footer.getByRole('link', { name, exact: true })).toBeVisible();
  }
});
