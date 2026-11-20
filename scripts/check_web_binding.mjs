/** Exercise the built Next gateway with a runtime-only private service URL. */
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const api = createServer(async (request, response) => {
  if (request.url === '/internal/api/v1/reject') {
    response.writeHead(401);
    response.end();
    return;
  }
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  if (request.url === '/internal/api/v1/redirect') {
    response.writeHead(302, { location: 'https://example.org/callback', 'set-cookie': ['one=1; HttpOnly; Path=/', 'two=2; HttpOnly; Path=/'] });
    response.end();
    return;
  }
  if (request.url === '/internal/api/v1/empty') {
    response.writeHead(204);
    response.end();
    return;
  }
  response.setHeader('content-type', 'application/json');
  response.end(JSON.stringify({
    path: request.url, method: request.method,
    body: Buffer.concat(chunks).toString(),
    cookie: request.headers.cookie,
    origin: request.headers.origin,
    authorization: request.headers.authorization,
    filename: request.headers['x-filename'],
    claimedIp: request.headers['x-rolewisp-client-ip'],
  }));
});
api.listen(0, '127.0.0.1');
await once(api, 'listening');
const apiPort = api.address().port;
const reserve = createServer();
reserve.listen(0, '127.0.0.1');
await once(reserve, 'listening');
const webPort = reserve.address().port;
await new Promise(resolve => reserve.close(resolve));
const web = spawn(process.execPath, ['node_modules/next/dist/bin/next', 'start', '--hostname', '127.0.0.1', '--port', String(webPort)], {
  cwd: `${root}apps/web`,
  env: { ...process.env, VERCEL: '', BACKEND_URL: `http://127.0.0.1:${apiPort}/internal` },
  stdio: 'ignore',
});
const origin = `http://127.0.0.1:${webPort}`;
try {
  let ready = false;
  for (let i = 0; i < 100; i++) {
    if (web.exitCode !== null) throw new Error('Next test server exited');
    try { ready = (await fetch(origin)).status === 200; } catch { /* Startup. */ }
    if (ready) break;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  assert.ok(ready, 'Next started');
  for (const method of ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']) {
    const response = await fetch(`${origin}/api/v1/probe?offset=25`, {
      method,
      headers: { origin, cookie: 'synthetic=1', authorization: 'Bearer synthetic-only', 'x-filename': 'sample.txt', 'x-rolewisp-client-ip': '192.0.2.1' },
      ...(method === 'GET' ? {} : { body: 'synthetic upload' }),
    });
    assert.equal(response.status, 200);
    assert.equal(response.headers.get('cache-control'), 'no-store');
    const data = await response.json();
    assert.equal(data.path, '/internal/api/v1/probe?offset=25');
    assert.equal(data.method, method);
    assert.equal(data.body, method === 'GET' ? '' : 'synthetic upload');
    assert.equal(data.cookie, 'synthetic=1');
    assert.equal(data.origin, origin);
    assert.equal(data.authorization, 'Bearer synthetic-only');
    assert.equal(data.filename, 'sample.txt');
    assert.equal(data.claimedIp, undefined, 'caller proxy metadata stripped');
  }
  assert.equal((await fetch(`${origin}/api/v1/empty`, { method: 'DELETE' })).status, 204);
  const head = await fetch(`${origin}/api/v1/probe`, { method: 'HEAD' });
  assert.equal(head.status, 200);
  assert.equal(await head.text(), '');
  assert.equal((await fetch(`${origin}/api/v1/reject`, { method: 'DELETE', body: 'synthetic' })).status, 401);
  assert.equal((await fetch(`${origin}/api/v1/probe`, { method: 'PUT', body: new Uint8Array(6 * 1024 * 1024 + 1) })).status, 413);
  const redirect = await fetch(`${origin}/api/v1/redirect`, { redirect: 'manual' });
  assert.equal(redirect.status, 302);
  assert.equal(redirect.headers.get('location'), 'https://example.org/callback');
  assert.equal(redirect.headers.getSetCookie().length, 2);
  assert.equal((await fetch(`${origin}/api/unsupported`)).status, 404);
  await new Promise(resolve => api.close(resolve));
  const unavailable = await fetch(`${origin}/api/v1/probe`);
  assert.equal(unavailable.status, 502);
  assert.equal(unavailable.headers.get('cache-control'), 'no-store');
  console.log('Runtime binding gateway passed: prefix/query, mutations/uploads, credentials, redirects, separate cookies, spoof stripping and unavailable-service handling');
} finally {
  web.kill('SIGTERM');
  if (api.listening) await new Promise(resolve => api.close(resolve));
  if (web.exitCode === null) await once(web, 'exit');
}
