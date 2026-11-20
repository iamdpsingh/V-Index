import { createHmac, randomBytes } from 'node:crypto';
import { isIP } from 'node:net';
import { NextRequest, NextResponse } from 'next/server';

export function proxy(request: NextRequest) {
  const headers = new Headers(request.headers);
  // Never forward a caller's claimed proxy identity.
  for (const name of ['x-rolewisp-client-ip', 'x-rolewisp-proxy-time', 'x-rolewisp-proxy-signature']) {
    headers.delete(name);
  }
  if (request.nextUrl.pathname.startsWith('/api/')) {
    const secret = process.env.PROXY_SHARED_SECRET || '';
    const address = request.headers.get('x-vercel-forwarded-for') || '';
    // Vercel supplies this header. Local/self-hosted requests cannot opt in by header.
    if (process.env.VERCEL === '1' && secret.length >= 32 && isIP(address)) {
      const stamp = Math.floor(Date.now() / 1000).toString();
      const message = `${stamp}\n${request.method}\n${request.nextUrl.pathname}\n${address}`;
      headers.set('x-rolewisp-client-ip', address);
      headers.set('x-rolewisp-proxy-time', stamp);
      headers.set('x-rolewisp-proxy-signature', createHmac('sha256', secret).update(message).digest('hex'));
    }
    return NextResponse.next({ request: { headers } });
  }
  const nonce = randomBytes(16).toString('base64');
  const dev = process.env.NODE_ENV === 'development';
  const reportURL = new URL('/api/v1/security/csp-report', request.url).href;
  const csp = [
    "default-src 'self'",
    `script-src 'nonce-${nonce}' 'strict-dynamic' 'report-sample'${dev ? " 'unsafe-eval'" : ''}`,
    // React components use style attributes; this does not permit inline scripts.
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self'",
    `connect-src 'self'${dev ? ' ws: wss:' : ''}`,
    "object-src 'none'", "base-uri 'none'", "frame-ancestors 'none'",
    "form-action 'self'", 'report-to csp', 'report-uri /api/v1/security/csp-report',
  ].join('; ');
  headers.set('Content-Security-Policy', csp);
  headers.set('x-nonce', nonce);
  const response = NextResponse.next({ request: { headers } });
  response.headers.set('Content-Security-Policy', csp);
  // Observe framework Trusted Types sinks before enforcement, without a bypass policy.
  response.headers.set('Content-Security-Policy-Report-Only', "require-trusted-types-for 'script'; report-to csp; report-uri /api/v1/security/csp-report");
  response.headers.set('Reporting-Endpoints', `csp="${reportURL}"`);
  response.headers.set('Cache-Control', 'private, no-store');
  response.headers.set('Cross-Origin-Opener-Policy', 'same-origin-allow-popups');
  response.headers.set('Cross-Origin-Resource-Policy', 'same-origin');
  return response;
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|icon.svg|fonts/).*)'],
};
