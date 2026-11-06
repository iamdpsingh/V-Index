'use client';

import { useEffect, useState } from 'react';
import { apiFetch, authLogout, getMe, type AccountOut, type Provider } from '../lib/api';
import AuthDialog from '../components/AuthDialog';
import CoveragePage from '../components/CoveragePage';
import JobSearch from '../components/JobSearch';
import RecommendationsView from '../components/RecommendationsView';
import { RolewispMark } from '../components/RolewispLogo';
import SourcesAdmin from '../components/SourcesAdmin';
import UserProfile from '../components/UserProfile';

export type Tab = 'jobs' | 'for-you' | 'profile' | 'sources' | 'coverage';

const TAB_HEADINGS: Record<Tab, string> = {
  jobs: 'Find your next opening.',
  'for-you': 'Tailored to your signals.',
  profile: 'Your private workspace.',
  sources: 'Keep the index current.',
  coverage: 'Coverage, with evidence.',
};

const TAB_SUBHEADINGS: Record<Tab, string> = {
  jobs: 'Real openings. Original sources. A clearer place to search.',
  'for-you': 'Explainable recommendations scored against your desired roles, skills, and resume.',
  profile: 'Manage your professional background, encrypted resume, and account security.',
  sources: 'Add a supported hosted career board and inspect its refresh history.',
  coverage:
    'Implementation and live verification are tracked separately for every required platform.',
};

export default function Home() {
  const [tab, setTab] = useState<Tab>('jobs');
  const [providers, setProviders] = useState<Provider[]>([]);
  const [token, setToken] = useState('');
  const [providerError, setProviderError] = useState('');
  const [account, setAccount] = useState<AccountOut | null>(null);
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');

  // Sync tab with URL search params on mount and on popstate
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    const t = params.get('tab') as Tab | null;
    if (t && ['jobs', 'for-you', 'profile', 'sources', 'coverage'].includes(t)) {
      setTab(t);
    }
    const handlePopState = () => {
      const p = new URLSearchParams(window.location.search);
      const curTab = p.get('tab') as Tab | null;
      if (curTab && ['jobs', 'for-you', 'profile', 'sources', 'coverage'].includes(curTab)) {
        setTab(curTab);
      }
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Check active account session on mount
  useEffect(() => {
    getMe()
      .then((me) => setAccount(me))
      .catch(() => setAccount(null));
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

  async function handleLogout() {
    try {
      await authLogout();
    } catch {
      // Ignore logout errors
    }
    setAccount(null);
    switchTab('jobs');
  }

  function handleAccountDeleted() {
    setAccount(null);
    switchTab('jobs');
  }

  // Counts for the index-note — LIVE_VERIFIED is evidence, not same as implemented
  const verifiedCount = providers.filter(
    (p) => (p.evidence_status || '').toUpperCase() === 'LIVE_VERIFIED'
  ).length;
  const totalCount = providers.length || 0;

  return (
    <>
      <header>
        <a className="wordmark" href="/" aria-label="Rolewisp — V-Index">
          <RolewispMark size={28} />
          <span className="brand-name">Rolewisp</span>
          <span className="brand-sub">V—Index</span>
        </a>
        <span className="header-note">Find your next opening.</span>

        <nav aria-label="Main navigation">
          {(['jobs', 'for-you', 'profile', 'sources', 'coverage'] as Tab[]).map((name) => (
            <button
              key={name}
              aria-current={tab === name ? 'page' : undefined}
              onClick={() => switchTab(name)}
            >
              {name === 'for-you' ? 'for you' : name}
            </button>
          ))}
        </nav>

        {/* Account indicator in header */}
        <div className="header-account">
          {account ? (
            <button
              type="button"
              className="account-pill-btn"
              onClick={() => switchTab('profile')}
              title={`Signed in as ${account.email}`}
            >
              <span className="account-dot" />
              <span className="account-email-label">{account.email}</span>
            </button>
          ) : (
            <button
              type="button"
              className="header-signin-btn"
              onClick={() => {
                setAuthMode('login');
                setAuthOpen(true);
              }}
            >
              Sign In
            </button>
          )}
        </div>
      </header>

      <main>
        <div className="eyebrow">
          THE INDEX / {tab === 'for-you' ? 'FOR YOU' : tab.toUpperCase()}
        </div>

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

        {tab === 'for-you' && (
          <RecommendationsView
            account={account}
            onOpenAuth={() => {
              setAuthMode('login');
              setAuthOpen(true);
            }}
            onGoToProfile={() => switchTab('profile')}
          />
        )}

        {tab === 'profile' &&
          (account ? (
            <UserProfile
              account={account}
              onLogout={handleLogout}
              onAccountDeleted={handleAccountDeleted}
            />
          ) : (
            <div className="empty auth-required-panel">
              <h2>Sign in to view your profile</h2>
              <p>
                Manage your desired job titles, professional skills, and encrypted resume.
              </p>
              <div className="empty-action-row">
                <button
                  type="button"
                  className="primary"
                  onClick={() => {
                    setAuthMode('login');
                    setAuthOpen(true);
                  }}
                >
                  Sign In →
                </button>
                <button
                  type="button"
                  className="filter-btn"
                  onClick={() => {
                    setAuthMode('register');
                    setAuthOpen(true);
                  }}
                >
                  Create Account
                </button>
              </div>
            </div>
          ))}

        {tab === 'coverage' && <CoveragePage providers={providers} />}

        {tab === 'sources' && (
          <SourcesAdmin token={token} onTokenChange={setToken} providers={providers} />
        )}
      </main>

      <AuthDialog
        isOpen={authOpen}
        initialMode={authMode}
        onClose={() => setAuthOpen(false)}
        onSuccess={(acc) => {
          setAccount(acc);
          if (tab === 'profile' || tab === 'for-you') {
            // Stay on current tab
          } else {
            switchTab('for-you');
          }
        }}
      />

      <footer>
        <span>Rolewisp — built in the V—Index repository</span>
        <span>Original sources. Visible evidence.</span>
        <a href="/docs" target="_blank" rel="noopener noreferrer">
          API documentation ↗
        </a>
      </footer>
    </>
  );
}
