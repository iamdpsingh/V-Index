'use client';

import { useState } from 'react';
import { type Provider } from '../lib/api';
import { formatDate, formatLabel } from '../lib/format';

interface CoveragePageProps {
  providers: Provider[];
}

type PlatformFilter = 'all' | 'ats' | 'job_board';

export default function CoveragePage({ providers }: CoveragePageProps) {
  const [filterKind, setFilterKind] = useState<PlatformFilter>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const implementedCount = providers.filter(
    (p) => p.implementation_status === 'IMPLEMENTED'
  ).length;
  const verifiedCount = providers.filter(
    (p) => p.evidence_status === 'LIVE_VERIFIED'
  ).length;
  const unimplementedCount = providers.filter(
    (p) => p.implementation_status === 'NOT_STARTED'
  ).length;

  const atsCount = providers.filter((p) => p.kind === 'ats').length;
  const boardCount = providers.filter((p) => p.kind === 'job_board').length;

  const filteredProviders = providers.filter((p) => {
    if (filterKind === 'ats' && p.kind !== 'ats') return false;
    if (filterKind === 'job_board' && p.kind !== 'job_board') return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchName = p.name.toLowerCase().includes(q);
      const matchLimitations = p.limitations.some((lim) => lim.toLowerCase().includes(q));
      const matchReason = (p.failure_reason || '').toLowerCase().includes(q);
      return matchName || matchLimitations || matchReason;
    }
    return true;
  });

  return (
    <>
      {/* Summary notice — distinct counts for implemented, verified, and unimplemented */}
      <div className="notice">
        {implementedCount} connectors implemented.{' '}
        {verifiedCount} have live evidence.{' '}
        {unimplementedCount} remain unimplemented.
      </div>

      {/* Filter and search controls for reviewers */}
      <div className="coverage-controls">
        <div className="filter-group" role="group" aria-label="Filter platforms by kind">
          <button
            type="button"
            className={`filter-btn ${filterKind === 'all' ? 'active' : ''}`}
            onClick={() => setFilterKind('all')}
          >
            All platforms ({providers.length})
          </button>
          <button
            type="button"
            className={`filter-btn ${filterKind === 'ats' ? 'active' : ''}`}
            onClick={() => setFilterKind('ats')}
          >
            ATS ({atsCount})
          </button>
          <button
            type="button"
            className={`filter-btn ${filterKind === 'job_board' ? 'active' : ''}`}
            onClick={() => setFilterKind('job_board')}
          >
            Job boards ({boardCount})
          </button>
        </div>

        <div className="search-filter">
          <input
            type="search"
            aria-label="Filter platforms by name"
            placeholder="Filter platform or limitation…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Full coverage table — all providers including unimplemented */}
      <div className="table-wrap">
        <table>
          <caption>Required ATS and job-board platforms</caption>
          <thead>
            <tr>
              <th>Platform</th>
              <th>Implementation</th>
              <th>Live evidence</th>
              <th>Jobs extracted</th>
              <th>Latest check / limitation</th>
            </tr>
          </thead>
          <tbody>
            {filteredProviders.length === 0 ? (
              <tr>
                <td colSpan={5} className="empty-table-cell">
                  No platforms matching “{searchQuery}”
                </td>
              </tr>
            ) : (
              filteredProviders.map((p) => (
                <tr key={p.name}>
                  <th scope="row">
                    {p.name}
                    <small>{p.kind === 'ats' ? 'ATS' : 'Job board'}</small>
                  </th>
                  <td>{formatLabel(p.implementation_status)}</td>
                  <td>
                    <span
                      className={`pill ${p.evidence_status === 'LIVE_VERIFIED' ? 'good' : ''}`}
                    >
                      {formatLabel(p.evidence_status)}
                    </span>
                  </td>
                  <td>{p.extraction_count ?? '—'}</td>
                  <td>
                    {formatDate(p.last_run_at)}
                    <small>
                      {p.failure_reason ||
                        (p.limitations.length > 0 ? p.limitations.join('; ') : '')}
                    </small>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}

