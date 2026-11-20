'use client';

import { useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import styles from './AnalyticsChoices.module.css';

type Choice = 'allow' | 'essential' | 'unset';

export default function AnalyticsChoices({ initialChoice, privacySignal }: {
  initialChoice: Choice; privacySignal: boolean;
}) {
  const [choice, setChoice] = useState(initialChoice);
  const router = useRouter();
  const pathname = usePathname();
  const settings = pathname === '/cookies';
  if (choice !== 'unset' && !settings) return null;

  function save(next: Choice) {
    document.cookie = `rolewisp_analytics=${next}; Path=/; Max-Age=15552000; SameSite=Lax${location.protocol === 'https:' ? '; Secure' : ''}`;
    const withdrawing = choice === 'allow' && next === 'essential';
    setChoice(next);
    if (withdrawing) {
      // End the old document and any third-party code when consent is withdrawn.
      location.reload();
    } else {
      router.refresh();
    }
  }

  return (
    <section className={`${styles.notice} ${settings ? styles.settings : ''}`} aria-label="Analytics preferences" id="analytics-preferences">
      <div>
        <h2>{settings ? 'Analytics preferences' : 'Your privacy choices'}</h2>
        <p>Essential cookies keep accounts working. With your permission, Vaya measures page views. <a href="/cookies">Read the cookie notice</a>.</p>
        {privacySignal && <p>Your browser privacy signal keeps optional analytics off.</p>}
        {settings && <p role="status">Optional analytics: {choice === 'allow' && !privacySignal ? 'allowed' : 'off'}.</p>}
      </div>
      <div className={styles.actions}>
        <button type="button" onClick={() => save('essential')}>Essential only</button>
        <button type="button" onClick={() => save('allow')} disabled={privacySignal}>Allow analytics</button>
      </div>
    </section>
  );
}
