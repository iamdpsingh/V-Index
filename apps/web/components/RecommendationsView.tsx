'use client';

import { useEffect, useState } from 'react';
import {
  getRecommendations,
  type AccountOut,
  type JobOut,
  type RecommendationItem,
  type RecommendationsOut,
} from '../lib/api';
import { formatDate, formatSalary } from '../lib/format';

interface RecommendationsViewProps {
  account: AccountOut | null;
  onOpenAuth: () => void;
  onGoToProfile: () => void;
}

const PAGE_SIZE = 20;

export default function RecommendationsView({
  account,
  onOpenAuth,
  onGoToProfile,
}: RecommendationsViewProps) {
  const [data, setData] = useState<RecommendationsOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<JobOut | null>(null);

  useEffect(() => {
    if (!account) return;
    loadRecommendations(offset);
  }, [account, offset]);

  async function loadRecommendations(currentOffset: number) {
    setLoading(true);
    setError('');
    try {
      const res = await getRecommendations({ limit: PAGE_SIZE, offset: currentOffset });
      setData(res);
      // Clear selected job if it is no longer in view
      if (selected && !res.items.some((item) => item.job.id === selected.id)) {
        setSelected(null);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load recommendations');
    } finally {
      setLoading(false);
    }
  }

  function handleSelectJob(job: JobOut) {
    setSelected(job);
  }

  function handleClearSelection() {
    setSelected(null);
  }

  function prevPage() {
    setOffset(Math.max(0, offset - PAGE_SIZE));
    setSelected(null);
  }

  function nextPage() {
    if (!data) return;
    setOffset(offset + PAGE_SIZE);
    setSelected(null);
  }

  // 1. Unauthenticated state
  if (!account) {
    return (
      <div className="recommendations-gate empty">
        <div className="eyebrow">TAILORED RECOMMENDATIONS</div>
        <h2>Private recommendations for your background.</h2>
        <p>
          Rolewisp matches open roles against the job titles and skills you save in your profile.
        </p>
        <div className="gate-actions">
          <button type="button" className="primary" onClick={onOpenAuth}>
            Sign in or create account →
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="recommendations-view">
      {/* Scope and explainability disclosure */}
      <div className="recs-disclosure-bar">
        <div className="disclosure-text">
          <span className="disclosure-method">
            Scoring: Title match (7×) · Skill match (3×) · Ranking scores are ordering signals, not fit percentages.
          </span>
          {data && (
            <span className="disclosure-scope">
              {data.truncated
                ? `Candidate pool limited to the newest ${data.candidate_limit.toLocaleString()} active openings.`
                : `Ranked across all ${data.total_candidates.toLocaleString()} current indexed roles.`}
            </span>
          )}
        </div>
        <button
          type="button"
          className="btn-refresh-recs"
          onClick={() => loadRecommendations(offset)}
          disabled={loading}
          title="Refresh recommendations with latest indexed roles"
        >
          {loading ? 'Refreshing…' : '↻ Refresh recommendations'}
        </button>
      </div>

      {error && (
        <div className="notice error recs-error" role="alert">
          {error}
        </div>
      )}

      {/* Needs preferences state */}
      {!loading && data?.needs_preferences && (
        <div className="empty preferences-needed">
          <h2>No matching signals configured.</h2>
          <p>
            Add desired job titles or skills to your profile to get recommendations.
          </p>
          <div className="empty-action-row">
            <button type="button" className="primary" onClick={onGoToProfile}>
              Configure profile signals →
            </button>
          </div>
        </div>
      )}

      {/* No matches state */}
      {!loading && !data?.needs_preferences && data?.items.length === 0 && (
        <div className="empty">
          <h2>No openings match your current profile signals.</h2>
          <p>
            Try adding additional skills or broader desired titles in your Profile, or check back
            soon as new sources are continuously indexed.
          </p>
        </div>
      )}

      {/* Ranked layout */}
      <div className={`job-layout ${selected ? 'has-selection' : ''}`}>
        <section
          aria-label="Recommended openings"
          aria-busy={loading}
          className="job-list-section"
        >
          {loading && <div className="loading-state">Scoring current openings…</div>}

          {!loading &&
            data?.items.map((item: RecommendationItem) => (
              <article
                key={item.job.id}
                className={`job-card ${selected?.id === item.job.id ? 'selected' : ''}`}
              >
                <div className="job-top">
                  <span className="job-company">{item.job.company}</span>
                  <div className="job-top-meta">
                    <span className="ref-number" title={`Index reference #${item.job.id}`}>
                      № {String(item.job.id).padStart(4, '0')}
                    </span>
                    <span className="pill rank-pill" title="Deterministic keyword score">
                      Weight: {item.rank_score}
                    </span>
                    <span className="pill">
                      {item.job.remote_status || 'Workplace unspecified'}
                    </span>
                  </div>
                </div>

                <h2>
                  <button
                    className="job-title"
                    onClick={() => handleSelectJob(item.job)}
                    aria-expanded={selected?.id === item.job.id}
                  >
                    {item.job.title}
                  </button>
                </h2>

                <p className="job-location">{item.job.location || 'Location unspecified'}</p>

                {/* Explicit matching reasons chips */}
                {item.reasons && item.reasons.length > 0 && (
                  <div className="reasons-bar">
                    {item.reasons.map((reason, i) => (
                      <span key={i} className="reason-chip">
                        ✓ {reason}
                      </span>
                    ))}
                  </div>
                )}

                <div className="job-bottom">
                  <span>{item.job.employment_type || 'Employment type unspecified'}</span>
                  {item.job.salary && formatSalary(item.job.salary) && (
                    <span className="salary-pill">{formatSalary(item.job.salary)}</span>
                  )}
                  <span>
                    {item.job.sources.length} {item.job.sources.length === 1 ? 'source' : 'sources'} ·
                    checked {formatDate(item.job.sources[0]?.last_checked_at ?? null)}
                  </span>
                </div>
              </article>
            ))}

          {/* Recommendations pagination */}
          {data && data.items.length > 0 && (
            <div className="pagination">
              <button disabled={loading || offset === 0} onClick={prevPage}>
                ← Previous
              </button>
              <span>
                {offset + 1}–{Math.min(offset + PAGE_SIZE, data.candidates_ranked)} of{' '}
                {data.candidates_ranked} matches
              </span>
              <button
                disabled={loading || offset + PAGE_SIZE >= data.candidates_ranked}
                onClick={nextPage}
              >
                Next →
              </button>
            </div>
          )}
        </section>

        {/* Selected job reader aside */}
        <aside className={selected ? 'mobile-visible' : ''}>
          {selected ? (
            <div className="job-record">
              <div className="mobile-return-bar">
                <button
                  type="button"
                  className="mobile-back-btn"
                  onClick={handleClearSelection}
                  aria-label="Return to recommendations"
                >
                  ← Return to recommendations
                </button>
              </div>

              <div className="record-header">
                <div className="eyebrow-row">
                  <span className="eyebrow">{selected.company}</span>
                  <span className="record-ref">№ {String(selected.id).padStart(4, '0')}</span>
                </div>
                <h2>{selected.title}</h2>
                <p className="record-location">{selected.location || 'Location unspecified'}</p>

                <div className="record-tags">
                  {selected.remote_status && (
                    <span className="pill">{selected.remote_status}</span>
                  )}
                  {selected.employment_type && (
                    <span className="pill">{selected.employment_type}</span>
                  )}
                  {selected.salary && formatSalary(selected.salary) && (
                    <span className="pill good">{formatSalary(selected.salary)}</span>
                  )}
                  {selected.published_at && (
                    <span className="pill" title="Original publication timestamp">
                      Published {new Date(selected.published_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>

              <div className="apply-action">
                {selected.application_url && selected.application_url.startsWith('https://') ? (
                  <a
                    className="apply"
                    href={selected.application_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Apply at original source ↗
                  </a>
                ) : (
                  <span className="apply non-link">Apply at original source ↗</span>
                )}
              </div>

              {selected.quality_flags && selected.quality_flags.length > 0 && (
                <div className="quality-notice" role="note">
                  {selected.quality_flags.includes('description_missing') ? (
                    <span>Original source omitted description text.</span>
                  ) : selected.quality_flags.includes('role_description_missing') ? (
                    <span>Role description omitted by source; other extracted sections shown below.</span>
                  ) : (
                    <span>Data quality note: {selected.quality_flags.join(', ')}</span>
                  )}
                </div>
              )}

              <h3>About the role</h3>
              <p className="description">
                {selected.description || 'The source did not provide a description.'}
              </p>

              {/* Quiet provenance rail with composite key */}
              <div className="provenance-section">
                <h3>Source history</h3>
                <div className="provenance-rail">
                  {selected.sources.map((s) => (
                    <div
                      key={`${s.source_id}-${s.source_url}-${s.application_url}`}
                      className="provenance-item"
                    >
                      <div className="prov-header">
                        <span
                          className={`status-badge ${
                            (s.status || '').toUpperCase() === 'ACTIVE' ? 'good' : ''
                          }`}
                        >
                          {s.status}
                        </span>
                        <span className="prov-time">checked {formatDate(s.last_checked_at)}</span>
                      </div>
                      <div className="prov-links">
                        <a
                          href={s.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="prov-link"
                        >
                          Original listing ↗
                        </a>
                        {s.application_url && s.application_url !== s.source_url && (
                          <a
                            href={s.application_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="prov-link"
                          >
                            Application target ↗
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="empty-aside">
              <div className="eyebrow">EXPLAINABLE MATCHING</div>
              <h2>Every match has explicit reasons.</h2>
              <p>
                Select a recommended role to inspect matching keywords, read the full requisition, and
                follow provenance back to the original source.
              </p>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

