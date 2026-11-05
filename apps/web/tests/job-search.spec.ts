import { test, expect } from '@playwright/test';
import {
  mockProviders, mockJobs, mockJobsEmpty,
  SAMPLE_JOB, LONG_JOB, MockJobs,
} from './fixtures/mock-server';

function oneJob(): MockJobs {
  return { total: 1, limit: 25, offset: 0, items: [SAMPLE_JOB] };
}

function manyJobs(count: number): MockJobs {
  const items = Array.from({ length: count }, (_, i) => ({
    ...SAMPLE_JOB, id: i + 1, external_id: `ext-${i + 1}`,
    title: `Engineer Role ${i + 1}`,
  }));
  return { total: count, limit: 25, offset: 0, items: items.slice(0, 25) };
}

test.beforeEach(async ({ page }) => {
  await mockProviders(page);
});

test('empty index state shows guidance message', async ({ page }) => {
  await mockJobsEmpty(page);
  await page.goto('/');
  await expect(page.getByText('No openings here yet.')).toBeVisible();
  await expect(page.getByText('Add a source')).toBeVisible();
});

test('displays job cards when jobs exist', async ({ page }) => {
  await mockJobs(page, oneJob());
  await page.goto('/');
  await expect(page.getByRole('article')).toBeVisible();
  await expect(page.getByText('Senior Engineer')).toBeVisible();
  await expect(page.getByText('Acme Corp')).toBeVisible();
});

test('results bar shows count', async ({ page }) => {
  await mockJobs(page, oneJob());
  await page.goto('/');
  await expect(page.getByText('1 open role')).toBeVisible();
});

test('results bar shows plural count', async ({ page }) => {
  await mockJobs(page, manyJobs(3));
  await page.goto('/');
  await expect(page.getByText('3 open roles')).toBeVisible();
});

test('clicking a job card opens detail aside', async ({ page }) => {
  await mockJobs(page, oneJob());
  await page.goto('/');
  await page.getByRole('button', { name: 'Senior Engineer' }).click();
  await expect(page.getByRole('link', { name: /Apply at original source/ })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'About the role' })).toBeVisible();
  await expect(page.getByText('A great role with interesting problems.')).toBeVisible();
});

test('description renders as plain text, not HTML', async ({ page }) => {
  const jobWithHtml = {
    ...SAMPLE_JOB,
    description: '<script>alert("xss")</script><b>Bold text</b>',
  };
  await mockJobs(page, { total: 1, limit: 25, offset: 0, items: [jobWithHtml] });
  await page.goto('/');
  await page.getByRole('button', { name: 'Senior Engineer' }).click();
  // Should show the raw string, not render as HTML
  const desc = page.locator('.description');
  await expect(desc).toContainText('<b>Bold text</b>');
  // No actual bold element rendered inside description
  await expect(desc.locator('b')).toHaveCount(0);
  await expect(desc.locator('script')).toHaveCount(0);
});

test('apply link has rel=noopener noreferrer when HTTPS', async ({ page }) => {
  await mockJobs(page, oneJob());
  await page.goto('/');
  await page.getByRole('button', { name: 'Senior Engineer' }).click();
  const applyLink = page.getByRole('link', { name: /Apply at original source/ });
  await expect(applyLink).toHaveAttribute('rel', 'noopener noreferrer');
  await expect(applyLink).toHaveAttribute('target', '_blank');
  const href = await applyLink.getAttribute('href');
  expect(href).toMatch(/^https:\/\//);
});

test('non-HTTPS apply link renders as text not anchor', async ({ page }) => {
  const job = { ...SAMPLE_JOB, application_url: 'http://insecure.example.com/apply' };
  await mockJobs(page, { total: 1, limit: 25, offset: 0, items: [job] });
  await page.goto('/');
  await page.getByRole('button', { name: 'Senior Engineer' }).click();
  // Should NOT be a link (no <a href=...> for the apply button)
  const applyLink = page.locator('a[href="http://insecure.example.com/apply"]');
  await expect(applyLink).toHaveCount(0);
  // The text is still shown
  await expect(page.getByText('Apply at original source ↗')).toBeVisible();
});

test('source history is shown in aside', async ({ page }) => {
  await mockJobs(page, oneJob());
  await page.goto('/');
  await page.getByRole('button', { name: 'Senior Engineer' }).click();
  await expect(page.getByRole('heading', { name: 'Source history' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Original listing ↗' })).toBeVisible();
});

test('keyword search submits and updates results bar', async ({ page }) => {
  let searchUrl = '';
  await page.route('**/api/v1/jobs**', async (route) => {
    searchUrl = route.request().url();
    await route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({ total: 1, limit: 25, offset: 0, items: [SAMPLE_JOB] }),
    });
  });
  await page.goto('/');
  await page.getByLabel('keyword').fill('engineer');
  await page.getByRole('button', { name: /Search jobs/ }).click();
  await expect(page.getByText('1 open role')).toBeVisible();
  expect(searchUrl).toContain('keyword=engineer');
});

test('keyboard: Enter in search field triggers search', async ({ page }) => {
  let callCount = 0;
  await page.route('**/api/v1/jobs**', async (route) => {
    callCount++;
    await route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({ total: 0, limit: 25, offset: 0, items: [] }),
    });
  });
  await page.goto('/');
  const initial = callCount;
  await page.getByLabel('keyword').fill('typescript');
  await page.getByLabel('keyword').press('Enter');
  await page.waitForTimeout(200);
  expect(callCount).toBeGreaterThan(initial);
});

test('pagination: Next button disabled when on last page', async ({ page }) => {
  await mockJobs(page, manyJobs(10));
  await page.goto('/');
  await expect(page.locator('.pagination').getByRole('button', { name: /Next/ })).toBeDisabled();
});

test('pagination: Previous button disabled on first page', async ({ page }) => {
  await mockJobs(page, manyJobs(10));
  await page.goto('/');
  await expect(page.locator('.pagination').getByRole('button', { name: /Previous/ })).toBeDisabled();
});

test('pagination: Next enabled when total > page size', async ({ page }) => {
  await mockJobs(page, { total: 50, limit: 25, offset: 0, items: Array.from({ length: 25 }, (_, i) => ({ ...SAMPLE_JOB, id: i + 1, external_id: `e${i}` })) });
  await page.goto('/');
  await expect(page.locator('.pagination').getByRole('button', { name: /Next/ })).toBeEnabled();
});

test('long job title and location render without truncation errors', async ({ page }) => {
  await mockJobs(page, { total: 1, limit: 25, offset: 0, items: [LONG_JOB] });
  await page.goto('/');
  await expect(page.getByRole('article')).toBeVisible();
  await page.getByRole('button', { name: /Staff Engineer/ }).click();
  // Long description renders
  const desc = page.locator('.description');
  await expect(desc).toBeVisible();
});

test('searching while busy shows Searching…', async ({ page }) => {
  const ctrl = { resolve: null as (() => void) | null };
  await page.route('**/api/v1/jobs**', async (route) => {
    await new Promise<void>((resolve) => { ctrl.resolve = resolve; });
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ total: 0, limit: 25, offset: 0, items: [] }) });
  });
  await page.goto('/');
  // While pending, aria-live region shows Searching…
  await expect(page.locator('[aria-live="polite"]')).toContainText('Searching…');
  if (ctrl.resolve) ctrl.resolve();
});
