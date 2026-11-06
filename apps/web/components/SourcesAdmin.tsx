'use client';

import { FormEvent, useState } from 'react';
import { apiFetch, type Provider, type RunOut, type SourceOut } from '../lib/api';
import { formatDate } from '../lib/format';

interface SourcesAdminProps {
  token: string;
  onTokenChange: (t: string) => void;
  providers?: Provider[];
}

function classifyError(e: Error): string {
  const msg = e.message;
  if (msg.includes('401') || msg.toLowerCase().includes('unauthorized')) {
    return 'Invalid token';
  }
  if (
    msg.includes('409') ||
    msg.toLowerCase().includes('already exists') ||
    msg.toLowerCase().includes('already registered')
  ) {
    return 'Source already exists';
  }
  if (msg.includes('422')) {
    return `Validation error: ${msg}`;
  }
  if (msg.includes('503') || msg.toLowerCase().includes('service unavailable')) {
    return 'Service unavailable — try again shortly';
  }
  if (msg.toLowerCase().includes('failed to fetch') || msg.toLowerCase().includes('networkerror')) {
    return 'Network error — check your connection and try again';
  }
  return msg;
}

export default function SourcesAdmin({
  token,
  onTokenChange,
  providers = [],
}: SourcesAdminProps) {
  const [sources, setSources] = useState<SourceOut[]>([]);
  const [runs, setRuns] = useState<RunOut[]>([]);
  const [sourceForm, setSourceForm] = useState({
    url: '',
    company: '',
    refresh_minutes: 360,
  });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const implementedNames = providers
    .filter((p) => p.implementation_status === 'IMPLEMENTED')
    .map((p) => p.name);

  const supportedText =
    implementedNames.length > 0
      ? `${implementedNames.join(', ')} hosted boards are supported in this release.`
      : 'Greenhouse, Lever, Ashby, SmartRecruiters, and Personio hosted boards are supported in this release.';

  async function loadSources() {
    setError('');
    setBusy(true);
    try {
      const [s, r] = await Promise.all([
        apiFetch<SourceOut[]>('sources', token),
        apiFetch<RunOut[]>('runs', token),
      ]);
      setSources(s);
      setRuns(r);
    } catch (e) {
      setError(classifyError(e as Error));
    } finally {
      setBusy(false);
    }
  }

  async function addSource(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError('');
    setMessage('');
    try {
      await apiFetch('sources', token, {
        method: 'POST',
        body: JSON.stringify({
          url: sourceForm.url,
          company: sourceForm.company,
          refresh_minutes: sourceForm.refresh_minutes,
        }),
      });
      setMessage('Source added. The worker will pick it up on its next cycle.');
      setSourceForm({ url: '', company: '', refresh_minutes: 360 });
      await loadSources();
    } catch (e) {
      setError(classifyError(e as Error));
    } finally {
      setBusy(false);
    }
  }

  async function scheduleRefresh(id: number) {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      await apiFetch(`sources/${id}/refresh`, token, { method: 'POST' });
      setMessage('Refresh scheduled. Reload status after the worker completes.');
      await loadSources();
    } catch (e) {
      setError(classifyError(e as Error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {error && (
        <div className="notice error" role="alert">
          {error}
        </div>
      )}

      <div className="admin-grid">
        {/* Add source panel */}
        <section className="panel">
          <h2>Connect a career board</h2>
          <p>{supportedText}</p>

          {/* Admin token — in-memory only, never persisted */}
          <label>
            Admin token
            <input
              type="password"
              autoComplete="off"
              value={token}
              onChange={(e) => onTokenChange(e.target.value)}
            />
          </label>

          <form onSubmit={addSource}>
            <label>
              Company name
              <input
                required
                maxLength={200}
                value={sourceForm.company}
                onChange={(e) => setSourceForm({ ...sourceForm, company: e.target.value })}
              />
            </label>
            <label>
              Hosted board URL
              <input
                type="url"
                required
                value={sourceForm.url}
                onChange={(e) => setSourceForm({ ...sourceForm, url: e.target.value })}
              />
            </label>
            <label>
              Refresh interval (minutes)
              <input
                type="number"
                min={60}
                max={10080}
                step={60}
                value={sourceForm.refresh_minutes}
                onChange={(e) =>
                  setSourceForm({
                    ...sourceForm,
                    refresh_minutes: Number(e.target.value),
                  })
                }
              />
            </label>
            <button className="primary" disabled={busy || !token} type="submit">
              Add source ↗
            </button>
          </form>

          <button
            className="text-button"
            disabled={busy || !token}
            onClick={loadSources}
          >
            Reload source status ↻
          </button>

          {message && <p role="status">{message}</p>}
        </section>

        {/* Connected sources */}
        <section>
          <h2>Connected sources</h2>
          {sources.length === 0 && (
            <p>Enter your admin token and load source status.</p>
          )}
          {sources.map((s) => (
            <article className="job-card" key={s.id}>
              <div className="job-top">
                <h3>{s.company}</h3>
                <span className="pill">{s.provider}</span>
              </div>
              <p>{s.url}</p>
              <p>
                {s.failures} consecutive failure{s.failures !== 1 ? 's' : ''} · next check{' '}
                {formatDate(s.next_check)}
              </p>
              <button disabled={busy} onClick={() => scheduleRefresh(s.id)}>
                Schedule refresh
              </button>
            </article>
          ))}
        </section>
      </div>

      {/* Recent fetch runs — includes finished_at column */}
      <h2 className="section-title">Recent fetch runs</h2>
      <div className="table-wrap">
        <table>
          <caption>Refresh status for connected sources</caption>
          <thead>
            <tr>
              <th>Run / Source</th>
              <th>Status</th>
              <th>Jobs</th>
              <th>Started</th>
              <th>Finished</th>
              <th>Error</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.id}>
                <td>
                  #{r.id} / #{r.source_id}
                </td>
                <td>
                  <span
                    className={`pill ${
                      r.status === 'SUCCESS' ? 'good' : r.status === 'FAILED' ? 'pill-fail' : ''
                    }`}
                  >
                    {r.status}
                  </span>
                </td>
                <td>{r.count}</td>
                <td>{formatDate(r.started_at)}</td>
                <td>{formatDate(r.finished_at)}</td>
                <td className={r.error ? 'cell-error' : ''}>{r.error || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
