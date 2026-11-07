import { test, expect } from '@playwright/test';
import { mockProviders, mockJobsEmpty } from './fixtures/mock-server';

test.beforeEach(async ({ page }) => {
  await mockProviders(page);
  await mockJobsEmpty(page);
  await page.goto('/');
});

test('Pricing tab is accessible from consumer navigation', async ({ page }) => {
  const pricingBtn = page.getByRole('navigation').getByRole('button', { name: 'Pricing' });
  await expect(pricingBtn).toBeVisible();
  await pricingBtn.click();

  await expect(page).toHaveURL(/tab=pricing/);
  await expect(page.getByRole('heading', { name: 'Find your next opening.' })).toBeVisible();
  await expect(page.getByText('Start free. Choose more when you need it.')).toBeVisible();
});

test('Free plan displays correctly with Start Searching CTA', async ({ page }) => {
  await page.goto('/?tab=pricing');

  const freeSection = page.getByRole('region', { name: 'Free plan' });
  await expect(freeSection).toBeVisible();
  await expect(freeSection.getByRole('heading', { name: 'Free' })).toBeVisible();
  await expect(freeSection.getByText('For everyday job discovery.')).toBeVisible();

  // CTA button switches to search
  const startBtn = freeSection.getByRole('button', { name: /Start searching/ });
  await expect(startBtn).toBeVisible();
  await expect(startBtn).toBeEnabled();
  await startBtn.click();

  // Should navigate back to jobs tab
  await expect(page.getByRole('navigation').getByRole('button', { name: 'Find jobs' })).toHaveAttribute('aria-current', 'page');
});

test('Plus plan displays Coming Soon badge and disabled CTA', async ({ page }) => {
  await page.goto('/?tab=pricing');

  const plusSection = page.getByRole('region', { name: 'Plus plan' });
  await expect(plusSection).toBeVisible();
  await expect(plusSection.getByRole('heading', { name: 'Plus' })).toBeVisible();
  await expect(plusSection.getByText('Coming soon')).toBeVisible();

  // Action button is disabled — no fake payment or checkout
  const disabledBtn = plusSection.getByRole('button', { name: /Paid membership opens later/ });
  await expect(disabledBtn).toBeVisible();
  await expect(disabledBtn).toBeDisabled();
  await expect(plusSection.getByText('Designed for a more focused search.')).toBeVisible();
});

test('Country and currency selector updates displayed prices', async ({ page }) => {
  await page.goto('/?tab=pricing');

  const select = page.getByRole('combobox', { name: /Select country for pricing/ });
  await expect(select).toBeVisible();

  // Select United States (USD)
  await select.selectOption('US');
  await expect(page.getByRole('region', { name: 'Plus plan' })).toContainText('$6');

  // Select Japan (JPY)
  await select.selectOption('JP');
  await expect(page.getByRole('region', { name: 'Plus plan' })).toContainText('900');

  // Select United Kingdom (GBP)
  await select.selectOption('GB');
  await expect(page.getByRole('region', { name: 'Plus plan' })).toContainText('5');
});

test('Pricing disclosure clarifies checkout status', async ({ page }) => {
  await page.goto('/?tab=pricing');
  await expect(page.getByText('Your country sets the displayed currency.')).toBeVisible();
  await expect(page.getByText(/Checkout is not accepting payments yet/)).toBeVisible();
});

