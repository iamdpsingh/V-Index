'use client';

import { useEffect, useState, type FormEvent } from 'react';
import { apiFetch, type AccountOut } from '../lib/api';

const roles = [
  ['candidate', 'Candidate'], ['agency', 'Hiring agency'],
  ['company', 'Company'], ['job_poster', 'Job poster'],
] as const;

const empty = { title: '', company: '', location: '', description: '', application_url: '' };
type Posting = typeof empty & { id: string; status: string };

export default function EmployerWorkspace({ account }: { account: AccountOut }) {
  const [role, setRole] = useState(account.role);
  const [postings, setPostings] = useState<Posting[]>([]);
  const [draft, setDraft] = useState(empty);
  const [editing, setEditing] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const employer = role && role !== 'candidate';

  useEffect(() => {
    if (employer) apiFetch<Posting[]>('me/postings').then(setPostings).catch(() => setError('Could not load postings.'));
  }, [employer]);

  async function update(action: () => Promise<void>) {
    setError('');
    setBusy(true);
    try { await action(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Could not save changes.'); }
    finally { setBusy(false); }
  }

  if (role === 'candidate') return null;
  return (
    <section className="profile-subcard">
      <h2>{employer ? 'Your job postings' : 'How will you use Rolewisp?'}</h2>
      {error && <p role="alert">{error}</p>}
      {!role && roles.map(([key, label]) => (
        <button key={key} className="btn-secondary" disabled={busy} type="button"
          onClick={() => void update(async () => {
            await apiFetch('me/role', '', { method: 'PUT', body: JSON.stringify({ role: key }) });
            setRole(key);
          })}>{label}</button>
      ))}
      {employer && (
        <>
          <form className="security-form" onSubmit={(event: FormEvent) => {
            event.preventDefault();
            void update(async () => {
              const job = await apiFetch<Posting>(editing ? `me/postings/${editing}` : 'me/postings', '', {
                method: editing ? 'PUT' : 'POST', body: JSON.stringify(draft),
              });
              setPostings((current) => [job, ...current.filter((row) => row.id !== job.id)]);
              setEditing(''); setDraft(empty);
            });
          }}>
            <label>Job title<input required maxLength={160} value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} /></label>
            <label>Company<input required maxLength={160} value={draft.company} onChange={(e) => setDraft({ ...draft, company: e.target.value })} /></label>
            <label>Location<input required maxLength={160} value={draft.location} onChange={(e) => setDraft({ ...draft, location: e.target.value })} /></label>
            <label>Description<textarea required maxLength={8000} value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })} /></label>
            <label>Application URL<input required type="url" maxLength={2048} value={draft.application_url} onChange={(e) => setDraft({ ...draft, application_url: e.target.value })} /></label>
            <button className="primary" disabled={busy}>{editing ? 'Save changes' : 'Save draft'}</button>
            {editing && <button type="button" onClick={() => { setEditing(''); setDraft(empty); }}>Cancel edit</button>}
          </form>
          {postings.map((job) => (
            <article key={job.id} className="job-card">
              <h3>{job.title}</h3><p>{job.status}</p>
              <button type="button" disabled={busy} onClick={() => {
                const { title, company, location, description, application_url } = job;
                setDraft({ title, company, location, description, application_url }); setEditing(job.id);
              }}>Edit</button>
              <button type="button" disabled={busy} onClick={() => void update(async () => {
                const action = job.status === 'published' ? 'close' : 'publish';
                const saved = await apiFetch<Posting>(`me/postings/${job.id}/${action}`, '', { method: 'POST' });
                setPostings((current) => current.map((row) => row.id === saved.id ? saved : row));
              })}>{job.status === 'published' ? 'Close posting' : 'Publish'}</button>
            </article>
          ))}
        </>
      )}
    </section>
  );
}
