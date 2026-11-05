'use client';

import { FormEvent, useEffect, useState } from 'react';
import { apiFetch, type JobOut, type SearchOut } from '../lib/api';
import { formatDate } from '../lib/format';

interface JobSearchProps {
  token: string;
  error: string;
  onError: (msg: string) => void;
}

const PAGE_SIZE = 25;

export default function JobSearch({ error, onError }: JobSearchProps) {
  const [filters, setFilters] = useState({ keyword: '', company: '', location: '' });
  const [applied, setApplied] = useState(filters);
  const [offset, setOffset] = useState(0);
  const [results, setResults] = useState<SearchOut>({ total: 0, items: [], limit: PAGE_SIZE, offset: 0 });
  const [busy, setBusy] = useState(true);
  const [selected, setSelected] = useState<JobOut | null>(null);

  useEffect(() => {
    let active = true;
    setBusy(true);
    onError('');

    apiFetch<SearchOut>(
      `jobs?${new URLSearchParams({
        ...applied,
        limit: String(PAGE_SIZE),
        offset: String(offset),
      })}`
    )
      .then((data) => {
        if (active) setResults(data);
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
  }, [applied, offset]); // eslint-disable-line react-hooks/exhaustive-deps

  function handleSearch(e: FormEvent) {
    e.preventDefault();
    setOffset(0);
    setApplied({ ...filters });
    setSelected(null);
  }

  function prevPage() {
    setOffset(Math.max(0, offset - PAGE_SIZE));
    setSelected(null);
  }

  function nextPage() {
    setOffset(offset + PAGE_SIZE);
    setSelected(null);
  }

  const totalPages = results.total;
  const rangeEnd = Math.min(offset + PAGE_SIZE, totalPages);
  const rangeLabel = totalPages
    ? `${offset + 1}–${rangeEnd} of ${totalPages}`
    : '0 results';

  return (
    <>
      {/* Search form */}
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

      {/* Job layout */}
      <div className="job-layout">
        {/* Results list */}
        <section aria-label="Search results" aria-busy={busy}>
          {/* Empty state */}
          {!busy && !error && results.items.length === 0 && (
            <div className="empty">
              <h2>No openings here yet.</h2>
              <p>Add a source and let its first refresh finish, or try broader filters.</p>
            </div>
          )}

          {/* Job cards */}
          {!busy &&
            results.items.map((job) => (
              <article
                key={job.id}
                className={`job-card ${selected?.id === job.id ? 'selected' : ''}`}
              >
                <div className="job-top">
                  <span>{job.company}</span>
                  <span className="pill">{job.remote_status || 'Workplace unspecified'}</span>
                </div>
                <h2>
                  <button
                    className="job-title"
                    onClick={() => setSelected(job)}
                    aria-expanded={selected?.id === job.id}
                  >
                    {job.title}
                  </button>
                </h2>
                <p>{job.location || 'Location unspecified'}</p>
                <div className="job-bottom">
                  <span>{job.employment_type || 'Employment type unspecified'}</span>
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

        {/* Detail aside */}
        <aside>
          {selected ? (
            <>
              <div className="eyebrow">{selected.company}</div>
              <h2>{selected.title}</h2>
              <p>{selected.location}</p>
              {selected.application_url.startsWith('https://') ? (
                <a
                  className="apply"
                  href={selected.application_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Apply at original source ↗
                </a>
              ) : (
                <span className="apply" title="Apply link unavailable or not HTTPS">
                  Apply at original source ↗
                </span>
              )}
              <h3>About the role</h3>
              <p className="description">
                {selected.description || 'The source did not provide a description.'}
              </p>
              <h3>Source history</h3>
              {selected.sources.map((s) => (
                <p key={s.source_id}>
                  <a href={s.source_url} target="_blank" rel="noopener noreferrer">
                    Original listing ↗
                  </a>
                  <br />
                  <small>
                    {s.status} · checked {formatDate(s.last_checked_at)}
                  </small>
                </p>
              ))}
            </>
          ) : (
            <>
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
            </>
          )}
        </aside>
      </div>
    </>
  );
}
