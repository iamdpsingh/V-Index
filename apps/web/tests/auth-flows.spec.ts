import { test, expect } from '@playwright/test';
import { mockJobsEmpty, mockProviders, mockProfile, mockResume, SAMPLE_ACCOUNT } from './fixtures/mock-server';

test.beforeEach(async ({ page }) => {
  await mockProviders(page);
  await mockJobsEmpty(page);
});

test('Sign In button in header opens Auth dialog with mode tabs', async ({ page }) => {
  await page.route('**/api/v1/me', async (route) => {
    await route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Authentication required' }) });
  });

  await page.goto('/');
  await page.getByRole('button', { name: 'Sign In' }).click();

  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('tab', { name: 'Sign In' })).toBeVisible();
  await expect(dialog.getByRole('tab', { name: 'Create Account' })).toBeVisible();
});

test('signup validates the minimum password length', async ({ page }) => {
  await page.route('**/api/v1/me', async (route) => {
    await route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Authentication required' }) });
  });

  await page.goto('/');
  await page.getByRole('button', { name: 'Sign In' }).click();

  const dialog = page.getByRole('dialog');
  await dialog.getByRole('tab', { name: 'Create Account' }).click();
  await dialog.getByLabel('Email address').fill('user@example.com');
  await dialog.getByLabel('Password').fill('shortpass');
  await dialog.getByRole('button', { name: /^create account$/i }).click();
  expect(await dialog.getByLabel('Password').evaluate((input: HTMLInputElement) => input.checkValidity())).toBe(false);
});

test('409 conflict displays "An account with this email already exists."', async ({ page }) => {
  await page.route('**/api/v1/me', async (route) => {
    await route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Authentication required' }) });
  });
  await page.route('**/api/v1/auth/register', async (route) => {
    await route.fulfill({
      status: 409,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Account with this email already exists' }),
    });
  });

  await page.goto('/');
  await page.getByRole('button', { name: 'Sign In' }).click();

  const dialog = page.getByRole('dialog');
  await dialog.getByRole('tab', { name: 'Create Account' }).click();
  await dialog.getByLabel('Email address').fill('existing@example.com');
  await dialog.getByLabel('Password').fill('validpassword123');
  await dialog.getByRole('button', { name: /^create account$/i }).click();

  await expect(dialog.locator('.auth-error')).toHaveText('An account with this email already exists.');
});

test('successful login opens the private profile and supports logout', async ({ page }) => {
  await page.route('**/api/v1/me', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Authentication required' }) });
    }
  });
  await page.route('**/api/v1/auth/login', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(SAMPLE_ACCOUNT),
    });
  });
  await page.route('**/api/v1/auth/logout', async (route) => {
    await route.fulfill({ status: 204 });
  });

  await mockProfile(page);
  await mockResume(page);
  await page.goto('/');
  await page.getByRole('button', { name: 'Sign In' }).click();

  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Email address').fill('alex@example.com');
  await dialog.getByLabel('Password').fill('validpassword123');
  await dialog.getByRole('button', { name: /^sign in$/i }).click();

  // The account control exposes the signed-in identity through its accessible name.
  await expect(dialog).not.toBeVisible();
  const accountPill = page.locator('.account-pill-btn');
  await expect(accountPill).toBeVisible();
  await expect(accountPill).toHaveAccessibleName('Account profile: alex@example.com');

  // Clicking email pill opens Profile tab
  await accountPill.click();
  await expect(page).toHaveURL(/tab=profile/);
  await page.locator('.profile-settings > summary').click();
  await page.getByRole('button', { name: 'Sign Out', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Sign In', exact: true })).toBeVisible();
});

