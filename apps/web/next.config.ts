import type { NextConfig } from 'next';
const config: NextConfig = {
  async rewrites() {
    return [{ source: '/docs', destination: `${process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000'}/docs` }, { source: '/openapi.json', destination: `${process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000'}/openapi.json` }, { source: '/api/:path*', destination: `${process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000'}/api/:path*` }];
  },
};
export default config;
