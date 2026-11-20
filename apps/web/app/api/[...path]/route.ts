/** Same-origin API gateway. Service bindings are read only inside this function. */
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

async function forward(request: Request) {
  const incoming = new URL(request.url);
  if (!incoming.pathname.startsWith('/api/v1/')) {
    return new Response(null, { status: 404 });
  }
  const base = process.env.BACKEND_URL || process.env.API_INTERNAL_URL ||
    (process.env.VERCEL ? '' : 'http://127.0.0.1:8000');
  if (!base) {
    return Response.json({ detail: 'API service is not configured' }, {
      status: 503, headers: { 'Cache-Control': 'no-store' },
    });
  }
  // Preserve a platform-supplied base prefix; never use caller input as a host.
  const target = new URL(base.endsWith('/') ? base : `${base}/`);
  target.pathname = target.pathname.replace(/\/$/, '') + incoming.pathname;
  target.search = incoming.search;
  const headers = new Headers();
  for (const name of [
    'accept', 'content-type', 'authorization', 'cookie', 'origin', 'x-filename',
    'x-rolewisp-client-ip', 'x-rolewisp-proxy-time', 'x-rolewisp-proxy-signature',
  ]) {
    const value = request.headers.get(name);
    if (value !== null) headers.set(name, value);
  }
  headers.set('accept-encoding', 'identity');
  // Bound uploads before forwarding. A known-length body also preserves early
  // upstream rejections (e.g. expired sessions) without a chunked-stream race.
  let body: ArrayBuffer | undefined;
  if (!['GET', 'HEAD'].includes(request.method) && request.body) {
    const reader = request.body.getReader();
    const chunks: Uint8Array[] = [];
    let size = 0;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > 6 * 1024 * 1024) {
        await reader.cancel();
        return Response.json({ detail: 'Upload exceeds gateway limit' }, {
          status: 413, headers: { 'Cache-Control': 'no-store' },
        });
      }
      chunks.push(value);
    }
    const bytes = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
    body = bytes.buffer;
  }
  try {
    const upstream = await fetch(target, {
      method: request.method,
      headers,
      body,
      redirect: 'manual',
      cache: 'no-store',
      signal: AbortSignal.timeout(30_000),
    });
    const responseHeaders = new Headers();
    for (const [name, value] of upstream.headers) {
      if (![
        'set-cookie', 'connection', 'keep-alive', 'transfer-encoding',
        'content-length', 'content-encoding', 'upgrade', 'proxy-authenticate',
        'proxy-authorization', 'trailer', 'te',
      ].includes(name)) responseHeaders.set(name, value);
    }
    // Keep separate cookies, including OAuth cleanup plus session creation.
    for (const cookie of upstream.headers.getSetCookie()) responseHeaders.append('set-cookie', cookie);
    responseHeaders.set('Cache-Control', 'no-store');
    const responseBody = request.method === 'HEAD' || [204, 205, 304].includes(upstream.status) ? null : upstream.body;
    return new Response(responseBody, { status: upstream.status, headers: responseHeaders });
  } catch {
    // Never log credential bodies, cookies, binding URLs or callback query strings.
    return Response.json({ detail: 'API service is temporarily unavailable' }, {
      status: 502, headers: { 'Cache-Control': 'no-store' },
    });
  }
}

export { forward as GET, forward as HEAD, forward as POST, forward as PUT, forward as PATCH, forward as DELETE, forward as OPTIONS };
