import { test, expect } from '@playwright/test';
import {
  mockAuth,
  mockJobsEmpty,
  mockProviders,
  mockRecommendations,
  SAMPLE_RECOMMENDATIONS,
} from './fixtures/mock-server';

test.beforeEach(async ({ page }) => {
  await mockProviders(page);
  await mockJobsEmpty(page);
});

test('unauthenticated user sees recommendation gate prompting sign in', async ({ page }) => {
  await page.route('**/api/v1/me', async (route) => {
    await route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Authentication required' }) });
  });

  await page.goto('/?tab=for-you');

  await expect(page.locator('.recommendations-gate')).toBeVisible();
  await expect(page.getByRole('button', { name: /Sign in or create account/ })).toBeVisible();
});

test('authenticated user sees recommendations with rank score and matching reason chips', async ({ page }) => {
  await mockAuth(page);
  await mockRecommendations(page, SAMPLE_RECOMMENDATIONS);

  await page.goto('/?tab=for-you');

  // Verify disclosure bar
  const disclosureBar = page.locator('.recs-disclosure-bar');
  await expect(disclosureBar).toBeVisible();
  await expect(disclosureBar).toContainText('Title match (7×) · Skill match (3×)');

  // Verify recommended role card
  const card = page.locator('.job-card').first();
  await expect(card).toBeVisible();
  await expect(card.locator('.job-company')).toHaveText('Acme Corp');
  await expect(card.locator('.rank-pill')).toHaveText('Weight: 10');

  // Verify explicit reasons
  await expect(card.locator('.reason-chip', { hasText: 'Matches desired role: Engineer' })).toBeVisible();
  await expect(card.locator('.reason-chip', { hasText: 'Matches skill: Python' })).toBeVisible();

  // Clicking role opens inspectable detail aside
  await card.getByRole('button', { name: 'Senior Engineer' }).click();
  await expect(page.locator('aside .job-record h2')).toHaveText('Senior Engineer');
});

test('needs_preferences prompt directs user to configure profile', async ({ page }) => {
  await mockAuth(page);
  await mockRecommendations(page, {
    items: [],
    total_candidates: 0,
    candidates_ranked: 0,
    candidate_limit: 1000,
    truncated: false,
    limit: 20,
    offset: 0,
    needs_preferences: true,
  });

  await page.goto('/?tab=for-you');

  await expect(page.locator('.preferences-needed')).toBeVisible();
  await expect(page.locator('.preferences-needed h2')).toHaveText('No matching signals configured.');

  // Click action switches tab to profile
  await page.getByRole('button', { name: 'Configure profile signals →' }).click();
  await expect(page).toHaveURL(/tab=profile/);
});

