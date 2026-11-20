import { expect, test } from '@playwright/test';
import { mockJobsEmpty, mockProviders } from './fixtures/mock-server';

// Never send synthetic browser-test visits to the live analytics provider.
test.beforeEach(async ({ page }) => {
  await page.route('https://vayahq.com/**', route => route.abort());
});

test('each HTML response has a fresh server nonce authorizing framework scripts', async ({ request }) => {
  const first = await request.get('/', { headers: { 'x-nonce': 'caller-nonce', 'Content-Security-Policy': "script-src 'nonce-caller-nonce'" } });
  const second = await request.get('/privacy');
  const csp = first.headers()['content-security-policy'];
  const nonce = csp.match(/'nonce-([^']+)'/)?.[1];
  expect(nonce).toBeTruthy();
  expect(csp).toContain("'strict-dynamic'");
  expect(csp).not.toContain('caller-nonce');
  expect(second.headers()['content-security-policy']).not.toContain(`'nonce-${nonce}'`);
  expect(first.headers()['cache-control']).toContain('no-store');
  const html = await first.text();
  const scripts = html.match(/<script\b[^>]*>/g) || [];
  expect(scripts.length).toBeGreaterThan(0);
  for (const script of scripts) expect(script).toContain(`nonce="${nonce}"`);
});

test('the browser blocks an unapproved parser script and accepts the server nonce', async ({ page }) => {
  await page.route('**/', async route => {
    const response = await route.fetch();
    const nonce = response.headers()['content-security-policy'].match(/'nonce-([^']+)'/)?.[1];
    expect(nonce).toBeTruthy();
    await route.fulfill({ response, body: `<!doctype html><html><head><title>CSP isolation test</title></head><body><script>window.__rolewispUnexpectedExecution = true</script><script nonce="${nonce}">window.__rolewispExpectedExecution = true</script></body></html>` });
  });
  await page.route('**/api/v1/security/csp-report', route => route.fulfill({ status: 204 }));
  await page.goto('/');
  expect(await page.evaluate(() => Reflect.get(window, '__rolewispUnexpectedExecution'))).toBeUndefined();
  expect(await page.evaluate(() => Reflect.get(window, '__rolewispExpectedExecution'))).toBe(true);
});

test('the actual application hydrates with the nonce policy', async ({ page }) => {
  await mockProviders(page);
  await mockJobsEmpty(page);
  await page.route('**/api/v1/security/csp-report', route => route.fulfill({ status: 204 }));
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByText('No openings here yet.')).toBeVisible();
  expect(errors).toEqual([]);
});


test('only the approved Vaya image beacon path is allowed', async ({ page }) => {
  await mockProviders(page);
  await mockJobsEmpty(page);
  await page.route('**/api/v1/security/csp-report', route => route.fulfill({ status: 204 }));
  const requested: string[] = [];
  await page.route('https://vayahq.com/**', async route => {
    const url = route.request().url();
    if (url.endsWith('.js')) {
      await route.fulfill({ contentType: 'application/javascript', body: '' });
      return;
    }
    requested.push(url);
    await route.fulfill({ contentType: 'image/png', body: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aAn8AAAAASUVORK5CYII=', 'base64') });
  });
  await page.goto('/');
  const outcomes = await page.evaluate(async () => {
    const urls = [
      'https://vayahq.com/api/beacon/cda76eb26359277eec5b1dff04e1bc96?d=synthetic-intercepted-test',
      'https://vayahq.com/api/beacon/another-tracker',
      'https://vayahq.com/unapproved-image.png',
    ];
    return Promise.all(urls.map(url => new Promise(resolve => {
      const image = new Image();
      image.onload = () => resolve('loaded');
      image.onerror = () => resolve('blocked');
      image.src = url;
    })));
  });
  expect(outcomes).toEqual(['loaded', 'blocked', 'blocked']);
  expect(requested).toEqual(['https://vayahq.com/api/beacon/cda76eb26359277eec5b1dff04e1bc96?d=synthetic-intercepted-test']);
});
