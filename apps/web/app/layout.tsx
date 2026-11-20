import type { Metadata } from 'next';
import { headers } from 'next/headers';
import './globals.css';

// A fresh nonce must authorize the framework scripts on every HTML response.
export const dynamic = 'force-dynamic';

export const metadata: Metadata = {
  title: 'Rolewisp | Find your next opening',
  description: 'A clear, transparent job index with original sources, scheduled refreshes, and verifiable evidence.',
  icons: {
    icon: '/icon.svg',
  },
};

export default async function Layout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const nonce = (await headers()).get('x-nonce') || undefined;
  return (
    <html lang="en">
      <head>
        <script async nonce={nonce} fetchPriority="low" src="https://vayahq.com/b/cda76eb26359277eec5b1dff04e1bc96.js" />
      </head>
      <body>{children}</body>
    </html>
  );
}
