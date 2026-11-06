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
  const [providerError, setProviderError] = useState('');

  // Sync tab with URL search params on mount and on popstate
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    const t = params.get('tab');
    if (t === 'jobs' || t === 'sources' || t === 'coverage') {
      setTab(t);
    }
    const handlePopState = () => {
      const p = new URLSearchParams(window.location.search);
      const curTab = p.get('tab');
      if (curTab === 'jobs' || curTab === 'sources' || curTab === 'coverage') {
        setTab(curTab);
      }
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Providers are fetched once at mount — used by both page intro and CoveragePage
  useEffect(() => {
    apiFetch<Provider[]>('providers')
      .then(setProviders)
      .catch((e: Error) => setProviderError(e.message));
  }, []);

  function switchTab(next: Tab) {
    setTab(next);
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      if (next === 'jobs') {
        params.delete('tab');
      } else {
        params.set('tab', next);
      }
      const q = params.toString();
      window.history.pushState(null, '', q ? `?${q}` : window.location.pathname);
    }
  }

  // Counts for the index-note — LIVE_VERIFIED is evidence, not same as implemented
  const verifiedCount = providers.filter(
    (p) => (p.evidence_status || '').toUpperCase() === 'LIVE_VERIFIED'
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

        {/* Global error banner (providers fetch only) */}
        {providerError && (
          <div className="notice error" role="alert">
            {providerError}
          </div>
        )}

        {tab === 'jobs' && <JobSearch token={token} />}

        {tab === 'coverage' && <CoveragePage providers={providers} />}

        {tab === 'sources' && (
          <SourcesAdmin token={token} onTokenChange={setToken} providers={providers} />
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
