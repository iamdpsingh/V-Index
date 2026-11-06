'use client';

import { FormEvent, useEffect, useState, useCallback } from 'react';
import { apiFetch, type JobOut, type SearchOut } from '../lib/api';
import { formatDate, formatSalary } from '../lib/format';

interface JobSearchProps {
  token: string;
  error: string;
  onError: (msg: string) => void;
}

const PAGE_SIZE = 25;

export default function JobSearch({ error, onError }: JobSearchProps) {
  const [filters, setFilters] = useState({ keyword: '', company: '', location: '' });
  const [applied, setApplied] = useState({ keyword: '', company: '', location: '' });
  const [offset, setOffset] = useState(0);
  const [results, setResults] = useState<SearchOut>({ total: 0, items: [], limit: PAGE_SIZE, offset: 0 });
  const [busy, setBusy] = useState(true);
  const [selected, setSelected] = useState<JobOut | null>(null);
  const [initialHydrated, setInitialHydrated] = useState(false);

  // Sync state from URL query parameters on initial mount and browser back/forward
  const readUrlState = useCallback(() => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    const q = params.get('q') || params.get('keyword') || '';
    const comp = params.get('company') || '';
    const loc = params.get('location') || '';
    const off = Math.max(0, parseInt(params.get('offset') || '0', 10) || 0);

    const newFilters = { keyword: q, company: comp, location: loc };
    setFilters(newFilters);
    setApplied(newFilters);
    setOffset(off);
    setInitialHydrated(true);
  }, []);

  useEffect(() => {
    readUrlState();
    const handlePopState = () => readUrlState();
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [readUrlState]);

  // Update URL search parameters when search/pagination changes
  const updateUrl = useCallback((newApplied: typeof applied, newOffset: number, selectedId?: number | null) => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams();
    if (newApplied.keyword) params.set('keyword', newApplied.keyword);
    if (newApplied.company) params.set('company', newApplied.company);
    if (newApplied.location) params.set('location', newApplied.location);
    if (newOffset > 0) params.set('offset', String(newOffset));
    if (selectedId) params.set('selected', String(selectedId));

    const newQuery = params.toString();
    const newUrl = newQuery ? `?${newQuery}` : window.location.pathname;
    window.history.pushState(null, '', newUrl);
  }, []);

  // Fetch jobs whenever applied filters or offset change
  useEffect(() => {
    if (!initialHydrated) return;
    let active = true;
    setBusy(true);
    onError('');

    const searchParams = new URLSearchParams({
      ...applied,
      limit: String(PAGE_SIZE),
      offset: String(offset),
    });

    apiFetch<SearchOut>(`jobs?${searchParams.toString()}`)
      .then((data) => {
        if (!active) return;
        setResults(data);

        // Check if URL specified a selected job ID
        if (typeof window !== 'undefined') {
          const params = new URLSearchParams(window.location.search);
          const selId = params.get('selected');
          if (selId) {
            const found = data.items.find((item) => String(item.id) === selId);
            if (found) setSelected(found);
          }
        }
      })
      .catch((e: Error) => {
        if (active) onError(e.message);
      })
      .finally(() => {
        if (active) setBusy(false);
      });

    return () => {
      active = false;
    };
  }, [applied, offset, initialHydrated]); // eslint-disable-line react-hooks/exhaustive-deps

  function handleSearch(e: FormEvent) {
    e.preventDefault();
    setOffset(0);
    setApplied({ ...filters });
    setSelected(null);
    updateUrl(filters, 0, null);
  }

  function handleSelectJob(job: JobOut) {
    setSelected(job);
    updateUrl(applied, offset, job.id);
  }

  function handleClearSelection() {
    setSelected(null);
    updateUrl(applied, offset, null);
  }

  function prevPage() {
    const nextOffset = Math.max(0, offset - PAGE_SIZE);
    setOffset(nextOffset);
    setSelected(null);
    updateUrl(applied, nextOffset, null);
  }

  function nextPage() {
    const nextOffset = offset + PAGE_SIZE;
    setOffset(nextOffset);
    setSelected(null);
    updateUrl(applied, nextOffset, null);
  }

  const totalPages = results.total;
  const rangeEnd = Math.min(offset + PAGE_SIZE, totalPages);
  const rangeLabel = totalPages
    ? `${offset + 1}–${rangeEnd} of ${totalPages}`
    : '0 results';

  return (
    <>
      {/* Search form — compact with clear labels */}
      <form className="search" onSubmit={handleSearch}>
        {(['keyword', 'company', 'location'] as const).map((key) => (
          <label key={key}>
            {key}
            <input
              value={filters[key]}
              placeholder={
                key === 'keyword'
                  ? 'Title or description'
                  : key === 'company'
                  ? 'Any company'
                  : 'Any location'
              }
              onChange={(e) => setFilters({ ...filters, [key]: e.target.value })}
            />
          </label>
        ))}
        <button className="primary" type="submit">
          Search jobs <span aria-hidden>↗</span>
        </button>
      </form>

      {/* Results bar */}
      <div className="results-bar">
        <span aria-live="polite">
          {busy
            ? 'Searching…'
            : `${results.total.toLocaleString()} open ${results.total === 1 ? 'role' : 'roles'}`}
        </span>
        <span>Recently indexed first</span>
      </div>

      {/* Job layout: searchable index on the left, inspectable job record on the right */}
      <div className={`job-layout ${selected ? 'has-selection' : ''}`}>
        {/* Results list */}
        <section aria-label="Search results" aria-busy={busy} className="job-list-section">
          {/* Empty state */}
          {!busy && !error && results.items.length === 0 && (
            <div className="empty">
              <h2>No openings here yet.</h2>
              <p>Add a source and let its first refresh finish, or try broader filters.</p>
            </div>
          )}

          {/* Job cards with reference index numbers */}
          {!busy &&
            results.items.map((job) => (
              <article
                key={job.id}
                className={`job-card ${selected?.id === job.id ? 'selected' : ''}`}
              >
                <div className="job-top">
                  <span className="job-company">{job.company}</span>
                  <div className="job-top-meta">
                    <span className="ref-number" title={`Index reference #${job.id}`}>
                      № {String(job.id).padStart(4, '0')}
                    </span>
                    <span className="pill">{job.remote_status || 'Workplace unspecified'}</span>
                  </div>
                </div>
                <h2>
                  <button
                    className="job-title"
                    onClick={() => handleSelectJob(job)}
                    aria-expanded={selected?.id === job.id}
                  >
                    {job.title}
                  </button>
                </h2>
                <p className="job-location">{job.location || 'Location unspecified'}</p>
                <div className="job-bottom">
                  <span>{job.employment_type || 'Employment type unspecified'}</span>
                  {job.salary && formatSalary(job.salary) && (
                    <span className="salary-pill">{formatSalary(job.salary)}</span>
                  )}
                  <span>
                    {job.sources.length} {job.sources.length === 1 ? 'source' : 'sources'} · checked{' '}
                    {formatDate(job.sources[0]?.last_checked_at ?? null)}
                  </span>
                </div>
              </article>
            ))}

          {/* Pagination */}
          <div className="pagination">
            <button disabled={busy || offset === 0} onClick={prevPage}>
              ← Previous
            </button>
            <span>{rangeLabel}</span>
            <button disabled={busy || offset + PAGE_SIZE >= results.total} onClick={nextPage}>
              Next →
            </button>
          </div>
        </section>

        {/* Detail aside / Inspectable job record */}
        <aside className={selected ? 'mobile-visible' : ''}>
          {selected ? (
            <div className="job-record">
              {/* Mobile return button */}
              <div className="mobile-return-bar">
                <button
                  type="button"
                  className="mobile-back-btn"
                  onClick={handleClearSelection}
                  aria-label="Return to search results"
                >
                  ← Return to results
                </button>
              </div>

              <div className="record-header">
                <div className="eyebrow-row">
                  <span className="eyebrow">{selected.company}</span>
                  <span className="record-ref">№ {String(selected.id).padStart(4, '0')}</span>
                </div>
                <h2>{selected.title}</h2>
                <p className="record-location">{selected.location || 'Location unspecified'}</p>

                {/* Metadata badges — only reserved when supplied by source */}
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

              {/* Apply action — verified HTTPS rel=noopener noreferrer */}
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
                  <span className="apply non-link" title="Apply destination is not a direct HTTPS link">
                    Apply at original source ↗
                  </span>
                )}
              </div>

              {/* Quality flags notice when description is omitted by source */}
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

              {/* Quiet provenance rail / Source history */}
              <div className="provenance-section">
                <h3>Source history</h3>
                <div className="provenance-rail">
                  {selected.sources.map((s) => (
                    <div key={s.source_id} className="provenance-item">
                      <div className="prov-header">
                        <span className={`status-badge ${s.status === 'ACTIVE' ? 'good' : ''}`}>
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
              <div className="eyebrow">TRACEABLE BY DESIGN</div>
              <h2>Every role has a source.</h2>
              <p>
                Select an opening to read its description, inspect where it came from and apply
                directly.
              </p>
              <div className="aside-rule" />
              <p>
                Listings are refreshed on a schedule. Missing roles need reconfirmation before they
                close.
              </p>
            </div>
          )}
        </aside>
      </div>
    </>
  );
}

