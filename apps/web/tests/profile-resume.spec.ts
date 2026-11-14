import { test, expect } from '@playwright/test';
import {
  mockAuth,
  mockJobsEmpty,
  mockProfile,
  mockProviders,
  mockResume,
  SAMPLE_PROFILE,
  SAMPLE_ACCOUNT,
  SAMPLE_RESUME,
} from './fixtures/mock-server';

test.beforeEach(async ({ page }) => {
  await mockProviders(page);
  await mockJobsEmpty(page);
  await mockAuth(page);
  await mockProfile(page);
  await mockResume(page);
});

test('profile screen loads saved name, headline, bio, desired roles, and skills', async ({ page }) => {
  await page.goto('/?tab=profile');

  // Verify form loaded with SAMPLE_PROFILE values
  await expect(page.getByLabel('Full name')).toHaveValue('Alex Morgan');
  await expect(page.getByLabel('Professional headline')).toHaveValue('Senior Systems Engineer');
  await expect(page.getByLabel('Current location')).toHaveValue('London, UK');
  await expect(page.locator('.profile-textarea')).toHaveValue(SAMPLE_PROFILE.bio);

  // Check tags
  await expect(page.locator('.interactive-tag', { hasText: 'Systems Engineer' })).toBeVisible();
  await expect(page.locator('.interactive-tag', { hasText: 'Python' })).toBeVisible();
});

test('adding desired role and skills updates tags and enables save', async ({ page }) => {
  let savedPayload: Record<string, unknown> | null = null;
  await page.route('**/api/v1/me/profile', async (route) => {
    if (route.request().method() === 'PUT') {
      savedPayload = route.request().postDataJSON();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ...SAMPLE_PROFILE, ...savedPayload }),
      });
    } else {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(SAMPLE_PROFILE),
      });
    }
  });

  await page.goto('/?tab=profile');

  // Add new desired title
  const titleInput = page.getByPlaceholder('e.g. Staff Software Engineer');
  await titleInput.fill('Principal Architect');
  await page.locator('.btn-add-tag', { hasText: 'Add' }).first().click();

  await expect(page.locator('.interactive-tag', { hasText: 'Principal Architect' })).toBeVisible();

  // Save profile
  await page.getByRole('button', { name: 'Save profile' }).click();
  await expect(page.locator('.success-notice')).toHaveText('Profile saved successfully.');

  expect(savedPayload).not.toBeNull();
  expect((savedPayload as unknown as Record<string, unknown>)?.desired_titles).toContain('Principal Architect');
});

test('resume section displays current file, size, and detected skill badges', async ({ page }) => {
  await page.goto('/?tab=profile');

  const resumeCard = page.locator('.resume-card');
  await expect(resumeCard).toBeVisible();
  await expect(resumeCard.locator('.resume-filename')).toHaveText('alex_morgan_cv.pdf');
  await expect(resumeCard).toContainText('application/pdf');

  // Detected skills list
  await expect(resumeCard.locator('.skill-chip', { hasText: 'Python' })).toBeVisible();
  await expect(resumeCard.locator('.skill-chip', { hasText: 'SQL' })).toBeVisible();
  await expect(resumeCard.locator('.skill-chip', { hasText: 'FastAPI' })).toBeVisible();
});

test('resume upload rejection preserves prior file visibility', async ({ page }) => {
  await page.route('**/api/v1/me/resume', async (route) => {
    if (route.request().method() === 'PUT') {
      await route.fulfill({
        status: 415,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Supported resume types are readable PDF, DOCX and UTF-8 TXT' }),
      });
    } else {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(SAMPLE_RESUME),
      });
    }
  });

  await page.goto('/?tab=profile');

  // Existing file visible
  await expect(page.locator('.resume-filename')).toHaveText('alex_morgan_cv.pdf');

  // Attempt replace with mock file
  const fileChooserPromise = page.waitForEvent('filechooser');
  await page.locator('.file-upload-label').click();
  const fileChooser = await fileChooserPromise;
  await fileChooser.setFiles({
    name: 'invalid_executable.exe',
    mimeType: 'application/octet-stream',
    buffer: Buffer.from('not a real resume'),
  });

  // Error message displayed
  await expect(page.locator('.resume-error')).toBeVisible();

  // Prior resume STILL visible
  await expect(page.locator('.resume-filename')).toHaveText('alex_morgan_cv.pdf');
});

test('employer reads postings and opens an editor only on demand', async ({ page }) => {
  const employer = { ...SAMPLE_ACCOUNT, role: 'employer' };
  await mockAuth(page, employer);
  const posting = {
    id: 'posting-1',
    title: 'Backend Engineer',
    company: 'Example Inc',
    location: 'Remote',
    description: 'Build data pipelines',
    application_url: 'https://example.com/jobs/1',
    status: 'draft',
  };
  await page.route('**/api/v1/me/postings', (route) => route.fulfill({ json: [posting] }));
  await page.route('**/api/v1/me/postings/posting-1', (route) => route.fulfill({
    json: { ...posting, ...route.request().postDataJSON() },
  }));

  await page.goto('/?tab=profile');
  await expect(page.getByText('Backend Engineer', { exact: true })).toBeVisible();
  await expect(page.getByLabel('Job title')).toHaveCount(0);

  const edit = page.getByRole('button', { name: 'Edit', exact: true });
  await edit.click();
  await expect(page.getByLabel('Job title')).toHaveValue(posting.title);
  await page.getByLabel('Job title').fill('Staff Engineer');
  await page.getByRole('button', { name: 'Save changes' }).click();
  await expect(page.getByText('Staff Engineer', { exact: true })).toBeVisible();
  await expect(page.getByLabel('Job title')).toHaveCount(0);
  await expect(edit).toBeFocused();

  await page.getByRole('button', { name: 'New posting' }).click();
  await expect(page.getByLabel('Job title')).toHaveValue('');
  await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  await expect(page.getByLabel('Job title')).toHaveCount(0);
});
