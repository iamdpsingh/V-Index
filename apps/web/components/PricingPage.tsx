'use client';

import { useEffect, useState, useTransition } from 'react';
import { getPlans, type PlansOut } from '../lib/api';

const SUPPORTED_COUNTRIES = [
  { code: 'US', label: 'United States (USD)' },
  { code: 'IN', label: 'India (INR)' },
  { code: 'GB', label: 'United Kingdom (GBP)' },
  { code: 'DE', label: 'Germany / Eurozone (EUR)' },
  { code: 'FR', label: 'France (EUR)' },
  { code: 'CA', label: 'Canada (CAD)' },
  { code: 'AU', label: 'Australia (AUD)' },
  { code: 'NZ', label: 'New Zealand (NZD)' },
  { code: 'SG', label: 'Singapore (SGD)' },
  { code: 'AE', label: 'United Arab Emirates (AED)' },
  { code: 'JP', label: 'Japan (JPY)' },
  { code: 'BR', label: 'Brazil (BRL)' },
  { code: 'MX', label: 'Mexico (MXN)' },
  { code: 'CH', label: 'Switzerland (CHF)' },
];

interface PricingPageProps {
  onStartSearching: () => void;
}

export function formatPlanPrice(amountMinor: number, currency: string, exponent: number): string {
  const amount = amountMinor / Math.pow(10, exponent);
  try {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency,
      minimumFractionDigits: exponent > 0 && amount % 1 !== 0 ? exponent : 0,
      maximumFractionDigits: exponent,
    }).format(amount);
  } catch {
    return `${currency} ${amount.toFixed(exponent)}`;
  }
}

export default function PricingPage({ onStartSearching }: PricingPageProps) {
  const [selectedCountry, setSelectedCountry] = useState<string>('');
  const [plansData, setPlansData] = useState<PlansOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [, startTransition] = useTransition();

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');

    getPlans(selectedCountry || undefined)
      .then((data) => {
        if (active) {
          setPlansData(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err instanceof Error ? err.message : 'Failed to load pricing catalogue');
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [selectedCountry]);

  const freePlan = plansData?.plans.find((p) => p.id === 'free');
  const plusPlan = plansData?.plans.find((p) => p.id === 'plus');

  return (
    <div className="pricing-page">
      <div className="pricing-header-row">
        <div>
          <h1 className="pricing-title">Find your next opening.</h1>
          <p className="pricing-subtitle">Start free. Choose more when you need it.</p>
        </div>

        <div className="pricing-country-selector">
          <label htmlFor="country-select" className="country-label">
            Country and currency
          </label>
          <select
            id="country-select"
            className="country-select-dropdown"
            value={selectedCountry}
            onChange={(e) => {
              const val = e.target.value;
              startTransition(() => {
                setSelectedCountry(val);
              });
            }}
            aria-label="Select country for pricing and currency"
          >
            <option value="">Select your country</option>
            {SUPPORTED_COUNTRIES.map((c) => (
              <option key={c.code} value={c.code}>
                {c.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="pricing-rule" />

      {error && (
        <div className="notice error pricing-error" role="alert">
          {error}
        </div>
      )}

      {plansData?.notice && (
        <div className="notice pricing-notice" role="note">
          {plansData.notice}
        </div>
      )}

      <div className="pricing-grid">
        {/* Free Plan Card */}
        <section className="pricing-card free-card" aria-label="Free plan">
          <div className="plan-title-row">
            <h2 className="plan-name">Free</h2>
          </div>

          <div className="plan-price-block">
            <span className="plan-price">
              {freePlan
                ? formatPlanPrice(freePlan.amount_minor, freePlan.currency, freePlan.currency_exponent)
                : '₹0'}
            </span>
            <span className="plan-period">/ month</span>
          </div>

          <p className="plan-description">For everyday job discovery.</p>

          <button
            type="button"
            className="plan-cta-btn free-cta-btn"
            onClick={onStartSearching}
            aria-label="Start searching with Free tier"
          >
            Start searching
          </button>

          <ul className="plan-features-list">
            <li>
              <span>Search jobs and open original applications</span>
            </li>
            <li>
              <span>Keep a profile and one resume</span>
            </li>
            <li>
              <span>Get job suggestions with readable reasons</span>
            </li>
          </ul>
        </section>

        <div className="pricing-card-divider" aria-hidden="true" />

        {/* Plus Plan Card */}
        <section className="pricing-card plus-card" aria-label="Plus plan">
          <div className="plan-title-row">
            <h2 className="plan-name">Plus</h2>
            <span className="plan-badge coming-soon-badge">Coming soon</span>
          </div>

          <div className="plan-price-block">
            <span className="plan-price">
              {plusPlan
                ? formatPlanPrice(plusPlan.amount_minor, plusPlan.currency, plusPlan.currency_exponent)
                : '₹399'}
            </span>
            <span className="plan-period">/ month</span>
          </div>

          <p className="plan-description">Planned price, before applicable taxes.</p>

          <button
            type="button"
            className="plan-cta-btn plus-cta-btn"
            disabled
            aria-label="Paid membership opens later — Coming soon"
          >
            Paid membership opens later
          </button>

          <div className="plus-future-block">
            <h3 className="plus-future-heading">Designed for a more focused search.</h3>
            <p className="plus-future-text">
              The paid tier will launch with its confirmed benefits and secure checkout. Free search stays available.
            </p>
          </div>
        </section>
      </div>

      <div className="pricing-rule" />

      <div className="pricing-footer-disclosure">
        <h3 className="disclosure-heading">Your country sets the displayed currency.</h3>
        <p className="disclosure-subtext">
          Select another country at any time. Checkout is not accepting payments yet.
        </p>
      </div>
    </div>
  );
}

