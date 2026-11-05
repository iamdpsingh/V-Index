'use client';

import { type Provider } from '../lib/api';
import { formatDate, formatLabel } from '../lib/format';

interface CoveragePageProps {
  providers: Provider[];
}

export default function CoveragePage({ providers }: CoveragePageProps) {
  const implementedCount = providers.filter(
    (p) => p.implementation_status === 'IMPLEMENTED'
  ).length;
  const verifiedCount = providers.filter(
    (p) => p.evidence_status === 'LIVE_VERIFIED'
  ).length;
  const unimplementedCount = providers.filter(
    (p) => p.implementation_status === 'NOT_STARTED'
  ).length;

  return (
    <>
      {/* Summary notice — separate counts for implemented vs verified */}
      <div className="notice">
        {implementedCount} connectors implemented.{' '}
        {verifiedCount} have live evidence.{' '}
        {unimplementedCount} remain unimplemented.
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
            {providers.map((p) => (
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
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
