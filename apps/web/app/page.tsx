'use client';

import { useEffect, useState } from 'react';
import { apiFetch, type Provider } from '../lib/api';
import CoveragePage from '../components/CoveragePage';
import JobSearch from '../components/JobSearch';
import SourcesAdmin from '../components/SourcesAdmin';

type Tab = 'jobs' | 'sources' | 'coverage';

const TAB_HEADINGS: Record<Tab, string> = {
  jobs: 'Find your next opening.',
  sources: 'Keep the index current.',
  coverage: 'Coverage, with evidence.',
};

const TAB_SUBHEADINGS: Record<Tab, string> = {
  jobs: 'Real openings. Original sources. A clearer place to search.',
  sources: 'Add a supported hosted career board and inspect its refresh history.',
  coverage:
    'Implementation and live verification are tracked separately for every required platform.',
};

export default function Home() {
  const [tab, setTab] = useState<Tab>('jobs');
  const [providers, setProviders] = useState<Provider[]>([]);
  const [token, setToken] = useState('');
  const [error, setError] = useState('');

  // Providers are fetched once at mount — used by both page intro and CoveragePage
  useEffect(() => {
    apiFetch<Provider[]>('providers').catch(() => {
      /* non-fatal: coverage tab will show empty table */
    });

    apiFetch<Provider[]>('providers')
      .then(setProviders)
      .catch((e: Error) => setError(e.message));
  }, []);

  function switchTab(next: Tab) {
    setTab(next);
    setError('');
  }

  // Counts for the index-note — LIVE_VERIFIED is evidence, not same as implemented
  const verifiedCount = providers.filter(
    (p) => p.evidence_status === 'LIVE_VERIFIED'
  ).length;
  const totalCount = providers.length || 0;

  return (
    <>
      <header>
        <a className="wordmark" href="/">
          V<span>—</span>Index
        </a>
        <span className="header-note">A source-first job index</span>
        <nav aria-label="Main navigation">
          {(['jobs', 'sources', 'coverage'] as Tab[]).map((name) => (
            <button
              key={name}
              aria-current={tab === name ? 'page' : undefined}
              onClick={() => switchTab(name)}
            >
              {name}
            </button>
          ))}
        </nav>
      </header>

      <main>
        <div className="eyebrow">THE INDEX / {tab.toUpperCase()}</div>

        <section className="intro">
          <div>
            <h1>{TAB_HEADINGS[tab]}</h1>
            <p>{TAB_SUBHEADINGS[tab]}</p>
          </div>
          {/* index-note: verified = live-checked evidence, not implemented count */}
          <div className="index-note">
            <span className="dot" />
            {verifiedCount} / {totalCount || '—'} platforms live-checked
            <small>Point-in-time evidence · initial release</small>
          </div>
        </section>

        {/* Global error banner (providers fetch or other top-level errors) */}
        {error && (
          <div className="notice error" role="alert">
            {error}
          </div>
        )}

        {tab === 'jobs' && (
          <JobSearch token={token} error={error} onError={setError} />
        )}

        {tab === 'coverage' && <CoveragePage providers={providers} />}

        {tab === 'sources' && (
          <SourcesAdmin token={token} onTokenChange={setToken} />
        )}
      </main>

      <footer>
        <span>V—Index</span>
        <span>Original sources. Visible evidence.</span>
        <a href="/docs" target="_blank" rel="noopener noreferrer">
          API documentation ↗
        </a>
      </footer>
    </>
  );
}
