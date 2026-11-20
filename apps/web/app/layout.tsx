import type { Metadata } from 'next';
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

export default function Layout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
