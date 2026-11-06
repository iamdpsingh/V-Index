import { test, expect } from '@playwright/test';
import { mockJobs, mockProviders, SAMPLE_JOB } from './fixtures/mock-server';

test.beforeEach(async ({ page }) => {
  await mockProviders(page);
});

test('refresh index button is visible and triggers fresh query', async ({ page }) => {
  let requestCount = 0;
  await page.route('**/api/v1/jobs**', async (route) => {
    requestCount++;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ total: 1, limit: 25, offset: 0, items: [SAMPLE_JOB] }),
    });
  });

  await page.goto('/');
  await expect(page.getByRole('button', { name: /Refresh index/ })).toBeVisible();

  // Polled timestamp appears in results bar
  await expect(page.locator('.polled-time')).toBeVisible();

  const initialCount = requestCount;
  // Click refresh
  await page.getByRole('button', { name: /Refresh index/ }).click();
  await expect(async () => {
    expect(requestCount).toBeGreaterThan(initialCount);
  }).toPass();
});

test('new results banner appears when background polling detects updates during reading', async ({ page }) => {
  let callCount = 0;
  await page.route('**/api/v1/jobs**', async (route) => {
    callCount++;
    if (callCount === 1) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ total: 1, limit: 25, offset: 0, items: [SAMPLE_JOB] }),
      });
    } else {
      const secondJob = { ...SAMPLE_JOB, id: 99, title: 'Lead Architect' };
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ total: 2, limit: 25, offset: 0, items: [SAMPLE_JOB, secondJob] }),
      });
    }
  });

  await page.goto('/');
  // Select first job to engage active reading view
  await page.getByRole('button', { name: 'Senior Engineer' }).click();
  await expect(page.locator('.job-record')).toBeVisible();

  // Trigger window focus event to fire live index poll
  await page.evaluate(() => {
    window.dispatchEvent(new Event('focus'));
  });

  // Banner should appear
  await expect(page.locator('.new-results-banner')).toBeVisible();
  await expect(page.locator('.new-results-banner')).toContainText('Fresh openings indexed');

  // Active reading view remains intact without displacement
  await expect(page.locator('.job-record h2')).toHaveText('Senior Engineer');

  // Clicking "Show updated results" updates the results
  await page.locator('.btn-update-results').click();
  await expect(page.locator('.new-results-banner')).not.toBeVisible();
});

