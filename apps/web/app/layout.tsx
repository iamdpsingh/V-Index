import type { Metadata } from 'next';
import { cookies, headers } from 'next/headers';
import AnalyticsChoices from '../components/AnalyticsChoices';
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
  const requestHeaders = await headers();
  const nonce = requestHeaders.get('x-nonce') || undefined;
  const preference = (await cookies()).get('rolewisp_analytics')?.value;
  const privacySignal = requestHeaders.get('sec-gpc') === '1' || requestHeaders.get('dnt') === '1';
  const choice = preference === 'allow' || preference === 'essential' ? preference : 'unset';
  return (
    <html lang="en">
      <head>
        {choice === 'allow' && !privacySignal && <script async nonce={nonce} fetchPriority="low" src="https://vayahq.com/b/cda76eb26359277eec5b1dff04e1bc96.js" />}
      </head>
      <body>
        {children}
        <AnalyticsChoices initialChoice={choice} privacySignal={privacySignal} />
      </body>
    </html>
  );
}
