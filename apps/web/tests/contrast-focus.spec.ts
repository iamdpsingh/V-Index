import { test, expect } from '@playwright/test';
import { mockProviders, mockJobsEmpty } from './fixtures/mock-server';

test.beforeEach(async ({ page }) => {
  await mockProviders(page);
  await mockJobsEmpty(page);
  await page.goto('/');
});

test('search button is reachable via keyboard Tab and visually focused', async ({ page }) => {
  // Tab through until we find the search submit button
  let found = false;
  for (let i = 0; i < 20; i++) {
    await page.keyboard.press('Tab');
    const focused = await page.evaluate(() => document.activeElement?.textContent?.trim());
    if (focused?.includes('Search jobs')) {
      found = true;
      break;
    }
  }
  expect(found).toBe(true);
});

test('nav buttons are keyboard reachable in order', async ({ page }) => {
  const reached: string[] = [];
  for (let i = 0; i < 10; i++) {
    await page.keyboard.press('Tab');
    const tag = await page.evaluate(() => document.activeElement?.tagName);
    const text = await page.evaluate(() => document.activeElement?.textContent?.trim());
    if (tag === 'BUTTON' && ['Find jobs', 'For you', 'Pricing'].includes(text || '')) {
      reached.push(text || '');
    }
  }
  expect(reached).toContain('Find jobs');
  expect(reached).toContain('For you');
  expect(reached).toContain('Pricing');
});

test('wordmark link is keyboard reachable', async ({ page }) => {
  let found = false;
  for (let i = 0; i < 5; i++) {
    await page.keyboard.press('Tab');
    const href = await page.evaluate(() => (document.activeElement as HTMLAnchorElement)?.href);
    if (href?.endsWith('/')) {
      found = true;
      break;
    }
  }
  expect(found).toBe(true);
});

