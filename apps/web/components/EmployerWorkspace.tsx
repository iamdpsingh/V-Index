'use client';

import { useEffect, useRef, useState, type FormEvent } from 'react';
import { apiFetch, type AccountOut } from '../lib/api';

const roles = [
  ['candidate', 'Candidate'], ['employer', 'Employer'],
] as const;

const empty = { title: '', company: '', location: '', description: '', application_url: '' };
type Posting = typeof empty & { id: string; status: string };

export default function EmployerWorkspace({ account }: { account: AccountOut }) {
  const [role, setRole] = useState(account.role);
  const [postings, setPostings] = useState<Posting[]>([]);
  const [draft, setDraft] = useState(empty);
  const [editor, setEditor] = useState<{ postingId?: string } | null>(null);
  const editorTitle = useRef<HTMLHeadingElement>(null);
  const editorTrigger = useRef<HTMLButtonElement>(null);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const employer = role === 'employer';

  useEffect(() => {
    if (!employer) return;
    apiFetch<Posting[]>('me/postings')
      .then((jobs) => { setPostings(jobs); setLoaded(true); })
      .catch(() => setError('Could not load postings.'));
  }, [employer]);

  useEffect(() => {
    if (editor) editorTitle.current?.focus();
  }, [editor]);

  useEffect(() => {
    if (!editor && !busy && editorTrigger.current) {
      editorTrigger.current.focus();
      editorTrigger.current = null;
    }
  }, [editor, busy]);

  function closeEditor() {
    setEditor(null);
    setDraft(empty);
  }

  async function update(action: () => Promise<void>) {
    setError('');
    setBusy(true);
    try { await action(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Could not save changes.'); }
    finally { setBusy(false); }
  }

  if (role === 'candidate') return null;
  return (
    <section className={employer ? "profile-card" : "profile-subcard"}>
      {error && <p className="notice error" role="alert">{error}</p>}
      {!role && (
        <form onSubmit={(event) => {
          event.preventDefault();
          const selected = new FormData(event.currentTarget).get('role');
          if (selected !== 'candidate' && selected !== 'employer') return;
          void update(async () => {
            await apiFetch('me/role', '', { method: 'PUT', body: JSON.stringify({ role: selected }) });
            setRole(selected);
          });
        }}>
          <fieldset className="role-options" disabled={busy}>
            <legend>How will you use Rolewisp?</legend>
            {roles.map(([key, label]) => (
              <label key={key}>
                <input type="radio" name="role" value={key} required />
                {label}
              </label>
            ))}
          </fieldset>
          <button className="btn-secondary" disabled={busy} type="submit">Continue</button>
        </form>
      )}
      {employer && (
        <>
          <header className="workspace-row">
            <h2>Your job postings</h2>
            <button type="button" className="btn-secondary" disabled={busy} onClick={(event) => {
              editorTrigger.current = event.currentTarget;
              setDraft(empty);
              setEditor({});
            }}>New posting</button>
          </header>

          {!loaded && !error && <p className="card-sub" role="status">Loading postings…</p>}
          {loaded && postings.length === 0 && !editor && (
            <p className="card-sub">You haven’t created a job posting yet.</p>
          )}
          {postings.map((job) => (
            <article key={job.id} className="workspace-row workspace-listing">
              <div>
                <h3>{job.title}</h3>
                <p>{job.company} · {job.location} · <span>{job.status}</span></p>
              </div>
              <div className="workspace-actions">
                <button type="button" className="btn-secondary" disabled={busy} onClick={(event) => {
                  const { title, company, location, description, application_url } = job;
                  editorTrigger.current = event.currentTarget;
                  setDraft({ title, company, location, description, application_url });
                  setEditor({ postingId: job.id });
                }}>Edit</button>
                <button type="button" className="btn-secondary" disabled={busy} onClick={() => void update(async () => {
                  const action = job.status === 'published' ? 'close' : 'publish';
                  const saved = await apiFetch<Posting>(`me/postings/${job.id}/${action}`, '', { method: 'POST' });
                  setPostings((current) => current.map((row) => row.id === saved.id ? saved : row));
                })}>{job.status === 'published' ? 'Close posting' : 'Publish'}</button>
              </div>
            </article>
          ))}

          {editor && (
            <section className="workspace-editor" aria-labelledby="workspace-editor-title">
              <h3 id="workspace-editor-title" ref={editorTitle} tabIndex={-1}>
                {editor.postingId ? 'Edit posting' : 'New posting'}
              </h3>
              <form className="profile-form" onSubmit={(event: FormEvent) => {
                event.preventDefault();
                const { postingId } = editor;
                void update(async () => {
                  const job = await apiFetch<Posting>(postingId ? `me/postings/${postingId}` : 'me/postings', '', {
                    method: postingId ? 'PUT' : 'POST', body: JSON.stringify(draft),
                  });
                  setPostings((current) => postingId
                    ? current.map((row) => row.id === job.id ? job : row)
                    : [job, ...current]);
                  closeEditor();
                });
              }}>
                <div className="form-row">
                  <label>Job title<input required maxLength={160} value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} /></label>
                  <label>Company<input required maxLength={160} value={draft.company} onChange={(e) => setDraft({ ...draft, company: e.target.value })} /></label>
                </div>
                <div className="form-row">
                  <label>Location<input required maxLength={160} value={draft.location} onChange={(e) => setDraft({ ...draft, location: e.target.value })} /></label>
                  <label>Application URL<input required type="url" maxLength={2048} value={draft.application_url} onChange={(e) => setDraft({ ...draft, application_url: e.target.value })} /></label>
                </div>
                <label>Description<textarea className="profile-textarea" rows={6} required maxLength={8000} value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })} /></label>
                <div className="workspace-actions">
                  <button type="submit" className="primary" disabled={busy}>{editor.postingId ? 'Save changes' : 'Save draft'}</button>
                  <button type="button" className="btn-secondary" disabled={busy} onClick={closeEditor}>Cancel</button>
                </div>
              </form>
            </section>
          )}
        </>
      )}
    </section>
  );
}
