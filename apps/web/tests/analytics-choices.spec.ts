import { expect, test } from '@playwright/test';
import { mockJobsEmpty, mockProviders } from './fixtures/mock-server';

test.use({ storageState: { cookies: [], origins: [] } });

test.beforeEach(async ({ page }) => {
  await mockProviders(page);
  await mockJobsEmpty(page);
  await page.route('https://vayahq.com/**', route => route.fulfill({ contentType: 'application/javascript', body: 'window.__analyticsChoiceLoaded=true;' }));
});

test('analytics stays absent until allowed and essential-only persists', async ({ page, context }) => {
  const response = await page.goto('/');
  expect(await response!.text()).not.toContain('src="https://vayahq.com/b/');
  await expect(page.getByRole('region', { name: 'Analytics preferences' })).toBeVisible();
  await page.getByRole('button', { name: 'Essential only', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Analytics preferences' })).toHaveCount(0);
  expect((await context.cookies()).find(c => c.name === 'rolewisp_analytics')?.value).toBe('essential');
  await page.reload();
  expect(await page.evaluate(() => Reflect.get(window, '__analyticsChoiceLoaded'))).toBeUndefined();
});

test('explicit allowance loads the shared script', async ({ page, context }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Allow analytics', exact: true }).click();
  await expect.poll(() => page.evaluate(() => Reflect.get(window, '__analyticsChoiceLoaded'))).toBe(true);
  expect((await context.cookies()).find(c => c.name === 'rolewisp_analytics')?.value).toBe('allow');
});

test('withdrawing consent clears the old document and keeps future pages untracked', async ({ page, context }) => {
  await context.addCookies([{ name: 'rolewisp_analytics', value: 'allow', url: 'http://127.0.0.1:3100' }]);
  await page.goto('/cookies');
  await expect.poll(() => page.evaluate(() => Reflect.get(window, '__analyticsChoiceLoaded'))).toBe(true);
  await page.getByRole('button', { name: 'Essential only', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Optional analytics: off');
  expect(await page.evaluate(() => Reflect.get(window, '__analyticsChoiceLoaded'))).toBeUndefined();
  await page.goto('/');
  expect(await page.evaluate(() => Reflect.get(window, '__analyticsChoiceLoaded'))).toBeUndefined();
});

test('browser privacy signals keep analytics off even with an older allowance', async ({ page, context }) => {
  await context.addCookies([{ name: 'rolewisp_analytics', value: 'allow', url: 'http://127.0.0.1:3100' }]);
  await page.setExtraHTTPHeaders({ 'Sec-GPC': '1' });
  const response = await page.goto('/cookies');
  expect(await response!.text()).not.toContain('src="https://vayahq.com/b/');
  await expect(page.getByRole('button', { name: 'Allow analytics', exact: true })).toBeDisabled();
  expect(await page.evaluate(() => Reflect.get(window, '__analyticsChoiceLoaded'))).toBeUndefined();
});
