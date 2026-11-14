import { test } from '@playwright/test';
import {
  mockAuth,
  mockJobs,
  mockProfile,
  mockProviders,
  mockRecommendations,
  mockResume,
  mockSources,
  SAMPLE_JOB,
  SAMPLE_PROFILE,
  SAMPLE_PROVIDERS,
  SAMPLE_RECOMMENDATIONS,
  SAMPLE_RESUME,
  SAMPLE_RUN_OUT,
  SAMPLE_SOURCE_OUT,
} from './fixtures/mock-server';
import fs from 'fs';
import path from 'path';

const SCREENSHOT_DIR = path.resolve(__dirname, 'evidence/screenshots');

test.beforeAll(async () => {
  if (!fs.existsSync(SCREENSHOT_DIR)) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  }
});

test('capture desktop search and detail screenshots', async ({ page, isMobile }) => {
  test.skip(isMobile, 'Desktop only');
  await mockProviders(page, SAMPLE_PROVIDERS);
  await mockJobs(page, {
    total: 3,
    limit: 25,
    offset: 0,
    items: [
      SAMPLE_JOB,
      {
        ...SAMPLE_JOB,
        id: 2,
        external_id: 'ext-2',
        title: 'Senior Systems Architect',
        company: 'Stripe',
        location: 'Seattle, WA',
        remote_status: 'Hybrid',
      },
      {
        ...SAMPLE_JOB,
        id: 3,
        external_id: 'ext-3',
        title: 'Backend Platform Engineer',
        company: 'Linear',
        location: 'Remote — Americas',
        remote_status: 'Remote',
      },
    ],
  });

  await page.goto('/');
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'desktop-search-index.png') });

  // Select job
  await page.getByRole('button', { name: 'Senior Engineer' }).click();
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'desktop-job-inspectable-record.png') });

  // Auth dialog preview
  await page.getByRole('button', { name: 'Sign In' }).click();
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'desktop-auth-dialog.png') });
  await page.keyboard.press('Escape');

  // Authenticated Profile preview
  await mockAuth(page);
  await mockProfile(page, SAMPLE_PROFILE);
  await mockResume(page, SAMPLE_RESUME);
  await page.goto('/?tab=profile');
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'desktop-profile-workspace.png') });

  // Recommendations preview
  await mockRecommendations(page, SAMPLE_RECOMMENDATIONS);
  await page.getByRole('navigation').getByRole('button', { name: 'For you' }).click();
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'desktop-for-you-recommendations.png') });

  // Pricing preview
  await page.getByRole('navigation').getByRole('button', { name: 'Pricing' }).click();
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'desktop-pricing-plans.png') });

  // Coverage page
  await page.getByRole('button', { name: 'coverage' }).click();
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'desktop-coverage-matrix.png') });

  // Sources page
  await mockSources(page, [SAMPLE_SOURCE_OUT], [SAMPLE_RUN_OUT]);
  await page.getByRole('button', { name: 'sources' }).click();
  await page.getByLabel('Admin token').fill('admin-secret-preview');
  await page.getByRole('button', { name: /Reload source status/ }).click();
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'desktop-source-operations.png') });
});

test('capture mobile screenshots', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'Mobile only');
  await mockProviders(page, SAMPLE_PROVIDERS);
  await mockJobs(page, {
    total: 1,
    limit: 25,
    offset: 0,
    items: [SAMPLE_JOB],
  });

  await page.goto('/');
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'mobile-search-results.png') });

  // Select job for mobile focused view
  await page.getByRole('button', { name: 'Senior Engineer' }).click();
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'mobile-job-detail-focused.png') });

  // Mobile profile preview
  await mockAuth(page);
  await mockProfile(page, SAMPLE_PROFILE);
  await mockResume(page, SAMPLE_RESUME);
  await page.goto('/?tab=profile');
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'mobile-profile-workspace.png') });
});
