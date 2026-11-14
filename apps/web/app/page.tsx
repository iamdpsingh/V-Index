'use client';

import { useEffect, useState } from 'react';
import { apiFetch, authLogout, getMe, type AccountOut, type Provider } from '../lib/api';
import AuthDialog from '../components/AuthDialog';
import CoveragePage from '../components/CoveragePage';
import JobSearch from '../components/JobSearch';
import PricingPage from '../components/PricingPage';
import RecommendationsView from '../components/RecommendationsView';
import { RolewispSymbol } from '../components/RolewispLogo';
import SourcesAdmin from '../components/SourcesAdmin';
import UserProfile from '../components/UserProfile';

export type Tab = 'jobs' | 'for-you' | 'pricing' | 'profile' | 'sources' | 'coverage';

const TAB_HEADINGS: Record<Tab, string> = {
  jobs: 'Find your next opening.',
  'for-you': 'Tailored to your signals.',
  pricing: 'Find your next opening.',
  profile: 'Your private workspace.',
  sources: 'Keep the index current.',
  coverage: 'Coverage, with evidence.',
};

const TAB_SUBHEADINGS: Record<Tab, string> = {
  jobs: 'Search by role, company, or location, then apply on the original site.',
  'for-you': 'Explainable recommendations scored against your desired roles, skills, and resume.',
  pricing: 'Start free. Choose more when you need it.',
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
    if (t && ['jobs', 'for-you', 'pricing', 'profile', 'sources', 'coverage'].includes(t)) {
      setTab(t);
    }
    const handlePopState = () => {
      const p = new URLSearchParams(window.location.search);
      const curTab = p.get('tab') as Tab | null;
      if (curTab && ['jobs', 'for-you', 'pricing', 'profile', 'sources', 'coverage'].includes(curTab)) {
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

  // Providers are fetched once at mount — used by reviewer CoveragePage & SourcesAdmin
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
    await authLogout();
    setAccount(null);
    switchTab('jobs');
  }

  function handleAccountDeleted() {
    setAccount(null);
    switchTab('jobs');
  }

  // Counts for the reviewer index-note — LIVE_VERIFIED is evidence, not same as implemented
  const verifiedCount = providers.filter(
    (p) => (p.evidence_status || '').toUpperCase() === 'LIVE_VERIFIED'
  ).length;
  const totalCount = providers.length || 0;

  return (
    <>
      <header>
        <div className="header-inner">
          <a className="wordmark" href="/" aria-label="Rolewisp home">
            <RolewispSymbol size={32} />
            <span className="brand-name">Rolewisp</span>
          </a>


          {/* Consumer navigation: Find jobs, For you, Pricing */}
          <nav className="header-nav" aria-label="Main navigation">
            <button
              type="button"
              className="nav-btn"
              aria-current={tab === 'jobs' ? 'page' : undefined}
              onClick={() => switchTab('jobs')}
            >
              Find jobs
            </button>
            <button
              type="button"
              className="nav-btn"
              aria-current={tab === 'for-you' ? 'page' : undefined}
              onClick={() => switchTab('for-you')}
            >
              For you
            </button>
            <button
              type="button"
              className="nav-btn"
              aria-current={tab === 'pricing' ? 'page' : undefined}
              onClick={() => switchTab('pricing')}
            >
              Pricing
            </button>
          </nav>

          {/* Account indicator in header */}
          <div className="header-account">
            {account ? (
              <button
                type="button"
                className="account-pill-btn"
                onClick={() => switchTab('profile')}
                title={`Signed in as ${account.email}`}
                aria-label={`Account profile: ${account.email}`}
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
        </div>
      </header>

      <main>
        {/* Render standard intro header for non-pricing views */}
        {!['jobs', 'pricing'].includes(tab) && (
          <section className={`intro ${['jobs', 'for-you'].includes(tab) ? 'intro-consumer' : ''}`}>
            <div>
              {tab === 'coverage' && <div className="eyebrow">REVIEWER DIAGNOSTICS / COVERAGE</div>}
              {tab === 'sources' && <div className="eyebrow">OPERATOR CONTROLS / SOURCES</div>}
              <h1>{TAB_HEADINGS[tab]}</h1>
              <p>{TAB_SUBHEADINGS[tab]}</p>
            </div>

            {/* Diagnostic index-note shown only on reviewer / operator screens */}
            {(tab === 'coverage' || tab === 'sources') && (
              <div className="index-note">
                <span className="dot" />
                {verifiedCount} / {totalCount || '—'} platforms live-checked
                <small>Point-in-time evidence · initial release</small>
              </div>
            )}
          </section>
        )}

        {/* Global error banner (providers fetch only) */}
        {providerError && (tab === 'coverage' || tab === 'sources') && (
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

        {tab === 'pricing' && (
          <PricingPage onStartSearching={() => switchTab('jobs')} />
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
              <div className="empty-action-row" style={{ justifyContent: 'center' }}>
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
        <div className="footer-inner">
          <div className="footer-brand">
            <span className="footer-brand-title">Rolewisp</span>
            <span>Search jobs and apply at the source.</span>
          </div>
          <nav className="footer-nav" aria-label="Policies">
            <a href="/privacy">Privacy</a>
            <a href="/cookies">Cookies</a>
            <a href="/terms">Terms</a>
            <a href="/refunds">Refunds</a>
          </nav>
        </div>
      </footer>
    </>
  );
}
