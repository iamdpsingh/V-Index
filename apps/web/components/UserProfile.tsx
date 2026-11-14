'use client';

import { FormEvent, useEffect, useRef, useState } from 'react';
import {
  confirmEmailVerification,
  requestEmailVerification,
  deleteAccount,
  getProfile,
  updateProfile,
  type AccountOut,
  type ProfileInput,
} from '../lib/api';
import EmployerWorkspace from './EmployerWorkspace';
import ProfilePhoto from './ProfilePhoto';
import ResumeSection from './ResumeSection';

interface UserProfileProps {
  account: AccountOut;
  onLogout: () => Promise<void>;
  onAccountDeleted: () => void;
}

function ProfileList({ title, items }: { title: string; items?: string[] }) {
  if (!items?.length) return null;
  return (
    <section className="candidate-section">
      <h3>{title}</h3>
      <ul>{items.map((item, index) => <li key={index}>{item}</li>)}</ul>
    </section>
  );
}

export default function UserProfile({
  account,
  onLogout,
  onAccountDeleted,
}: UserProfileProps) {
  const [verified, setVerified] = useState(account.email_verified);
  const [code, setCode] = useState('');
  const [emailPending, setEmailPending] = useState(false);
  const [emailNotice, setEmailNotice] = useState('');
  const [emailError, setEmailError] = useState('');
  const [codeSent, setCodeSent] = useState(false);

  async function verifyEmail(confirm: boolean) {
    setEmailPending(true);
    setEmailError('');
    setEmailNotice('');
    try {
      if (confirm) {
        await confirmEmailVerification(code);
        setVerified(true);
        setCode('');
      } else {
        await requestEmailVerification();
        setCodeSent(true);
        setEmailNotice('Check your inbox for an 8-digit code.');
      }
    } catch (err) {
      setEmailError(err instanceof Error ? err.message : 'Could not verify your email.');
    } finally {
      setEmailPending(false);
    }
  }

  const [logoutPending, setLogoutPending] = useState(false);
  const [logoutError, setLogoutError] = useState('');

  async function signOut() {
    setLogoutPending(true);
    setLogoutError('');
    try {
      await onLogout();
    } catch {
      setLogoutError('Could not sign out. Please try again.');
    } finally {
      setLogoutPending(false);
    }
  }

  const [profile, setProfile] = useState<ProfileInput>({
    full_name: '',
    headline: '',
    location: '',
    bio: '',
    desired_titles: [],
    skills: [],
    preferred_locations: [],
    remote_only: false,
    use_resume_skills: true,
    experience_years: null,
  });

  const [editing, setEditing] = useState(false);
  const savedProfile = useRef<ProfileInput | null>(null);
  const editingStarted = useRef(false);
  const editButton = useRef<HTMLButtonElement>(null);
  const formHeading = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    if (editing) {
      editingStarted.current = true;
      formHeading.current?.focus();
    } else if (editingStarted.current) {
      editButton.current?.focus();
    }
  }, [editing]);

  function cancelEditing() {
    if (savedProfile.current) setProfile(savedProfile.current);
    setNewTitle('');
    setNewSkill('');
    setNewLoc('');
    setError('');
    setEditing(false);
  }

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [error, setError] = useState('');

  // Tag inputs state
  const [newTitle, setNewTitle] = useState('');
  const [newSkill, setNewSkill] = useState('');
  const [newLoc, setNewLoc] = useState('');

  // Account deletion state
  const [deletePw, setDeletePw] = useState('');
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  useEffect(() => {
    loadProfileData();
  }, []);

  async function loadProfileData() {
    setLoading(true);
    setError('');
    try {
      const data = await getProfile();
      const saved = {
        education: data.education || [],
        experience: data.experience || [],
        projects: data.projects || [],
        links: data.links || [],
        full_name: data.full_name || '',
        headline: data.headline || '',
        location: data.location || '',
        bio: data.bio || '',
        desired_titles: data.desired_titles || [],
        skills: data.skills || [],
        preferred_locations: data.preferred_locations || [],
        remote_only: Boolean(data.remote_only),
        use_resume_skills: data.use_resume_skills ?? true,
        experience_years: data.experience_years ?? null,
      };
      savedProfile.current = saved;
      setProfile(saved);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load profile');
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveProfile(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError('');
    setSaveSuccess(false);

    try {
      const payload: ProfileInput = {
        education: (profile.education ?? []).map((line) => line.trim()).filter(Boolean),
        experience: (profile.experience ?? []).map((line) => line.trim()).filter(Boolean),
        projects: (profile.projects ?? []).map((line) => line.trim()).filter(Boolean),
        links: profile.links || [],
        full_name: profile.full_name || '',
        headline: profile.headline || '',
        location: profile.location || '',
        bio: profile.bio || '',
        desired_titles: profile.desired_titles || [],
        skills: profile.skills || [],
        preferred_locations: profile.preferred_locations || [],
        remote_only: profile.remote_only ?? false,
        use_resume_skills: profile.use_resume_skills ?? true,
        experience_years:
          profile.experience_years !== null && profile.experience_years !== undefined
            ? Number(profile.experience_years)
            : null,
      };

      const updated = await updateProfile(payload);
      const saved = {
        education: updated.education || [],
        experience: updated.experience || [],
        projects: updated.projects || [],
        links: updated.links || [],
        full_name: updated.full_name || '',
        headline: updated.headline || '',
        location: updated.location || '',
        bio: updated.bio || '',
        desired_titles: updated.desired_titles || [],
        skills: updated.skills || [],
        preferred_locations: updated.preferred_locations || [],
        remote_only: Boolean(updated.remote_only),
        use_resume_skills: updated.use_resume_skills ?? true,
        experience_years: updated.experience_years ?? null,
      };
      savedProfile.current = saved;
      setProfile(saved);
      cancelEditing();
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 4000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to save profile');
    } finally {
      setSaving(false);
    }
  }

  // Tag list helpers
  function addTag(key: 'desired_titles' | 'skills' | 'preferred_locations', value: string) {
    const trimmed = value.trim();
    if (!trimmed) return;
    const current = profile[key] || [];
    if (!current.includes(trimmed)) {
      setProfile({ ...profile, [key]: [...current, trimmed] });
    }
  }

  function removeTag(key: 'desired_titles' | 'skills' | 'preferred_locations', index: number) {
    const current = [...(profile[key] || [])];
    current.splice(index, 1);
    setProfile({ ...profile, [key]: current });
  }

  async function handleDeleteAccount(e: FormEvent) {
    e.preventDefault();
    setDeleteError('');
    setDeleting(true);

    try {
      await deleteAccount({ password: deletePw });
      onAccountDeleted();
    } catch (err: unknown) {
      setDeleteError(err instanceof Error ? err.message : 'Account deletion failed');
      setDeleting(false);
    }
  }

  return (
    <div className="profile-container">
      {/* Account identity bar */}
      <div className="account-identity-bar">
        <ProfilePhoto key={account.id} />
        <div className="identity-info">
          <span className="identity-email">{account.email}</span>
          <span className="identity-meta">
            Joined {new Date(account.created_at).toLocaleDateString()} · Private profile
          </span>
        </div>
        <button type="button" className="btn-secondary logout-btn" onClick={signOut} disabled={logoutPending}>
          Sign Out
        </button>
        {logoutError && <p role="alert">{logoutError}</p>}
      </div>

      <EmployerWorkspace key={account.id} account={account} />

      {loading ? (
        <div className="loading-state">Loading your profile…</div>
      ) : (
        <div className="profile-grid">
          {/* Main profile form */}
          <section className="profile-card">
            <header className="workspace-row">
              <h2 ref={formHeading} tabIndex={-1}>{editing ? 'Edit profile' : 'Candidate profile'}</h2>
              {!editing && savedProfile.current && (
                <button type="button" className="btn-secondary" ref={editButton} onClick={() => {
                  setSaveSuccess(false);
                  setEditing(true);
                }}>Edit profile</button>
              )}
            </header>
            {error && (
              <div className="notice error profile-error" role="alert">
                {error}
              </div>
            )}

            {saveSuccess && (
              <div className="notice success-notice" role="status">
                Profile saved successfully.
              </div>
            )}

            {!savedProfile.current && (
              <button type="button" className="btn-secondary" onClick={() => void loadProfileData()}>Retry loading profile</button>
            )}
            {savedProfile.current && !editing && (
              <div className="candidate-summary">
                <div className="candidate-intro">
                  <h3>{profile.full_name || 'Your professional profile'}</h3>
                  {profile.headline && <p>{profile.headline}</p>}
                  {(profile.location || profile.experience_years != null) && (
                    <p className="candidate-meta">
                      {[profile.location, profile.experience_years != null
                        ? `${profile.experience_years} ${profile.experience_years === 1 ? 'year' : 'years'} of experience`
                        : ''].filter(Boolean).join(' · ')}
                    </p>
                  )}
                  {!profile.full_name && !profile.headline && !profile.bio && (
                    <p className="candidate-meta">Add your background and job preferences to get more relevant recommendations.</p>
                  )}
                </div>
                {profile.bio && <section className="candidate-section"><h3>About</h3><p>{profile.bio}</p></section>}
                <ProfileList title="Experience" items={profile.experience} />
                <ProfileList title="Education" items={profile.education} />
                <ProfileList title="Projects" items={profile.projects} />
                <ProfileList title="Skills" items={profile.skills} />
                <ProfileList title="Roles of interest" items={profile.desired_titles} />
                <ProfileList title="Preferred locations" items={profile.remote_only
                  ? [...(profile.preferred_locations ?? []), 'Remote only']
                  : profile.preferred_locations} />
                {!!profile.links?.length && (
                  <section className="candidate-section">
                    <h3>Links</h3>
                    <ul>{profile.links.filter((link) => link.url.startsWith('https://')).map((link, index) => (
                      <li key={index}><a href={link.url} target="_blank" rel="noopener noreferrer">{link.label || link.url}</a></li>
                    ))}</ul>
                  </section>
                )}
              </div>
            )}
            {editing && <form onSubmit={handleSaveProfile} className="profile-form candidate-edit-form">
              <div className="form-row">
                <label>
                  Full name
                  <input
                    value={profile.full_name || ''}
                    maxLength={100}
                    placeholder="e.g. Alex Morgan"
                    onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
                  />
                </label>

                <label>
                  Professional headline
                  <input
                    value={profile.headline || ''}
                    maxLength={160}
                    placeholder="e.g. Senior Backend Engineer"
                    onChange={(e) => setProfile({ ...profile, headline: e.target.value })}
                  />
                </label>
              </div>

              <div className="form-row">
                <label>
                  Current location
                  <input
                    value={profile.location || ''}
                    maxLength={100}
                    placeholder="e.g. London, UK"
                    onChange={(e) => setProfile({ ...profile, location: e.target.value })}
                  />
                </label>

                <label>
                  Years of experience
                  <input
                    type="number"
                    min={0}
                    max={60}
                    value={profile.experience_years ?? ''}
                    placeholder="e.g. 5"
                    onChange={(e) => {
                      const val = e.target.value;
                      setProfile({
                        ...profile,
                        experience_years: val === '' ? null : parseInt(val, 10),
                      });
                    }}
                  />
                </label>
              </div>

              <label>
                Professional bio
                <textarea
                  rows={3}
                  maxLength={2000}
                  value={profile.bio || ''}
                  placeholder="Brief summary of your background, technical interests, and experience…"
                  onChange={(e) => setProfile({ ...profile, bio: e.target.value })}
                  className="profile-textarea"
                />
              </label>

              {/* Desired Titles */}
              <div className="tag-field-group">
                <label>Desired job titles</label>
                <div className="tag-input-row">
                  <input
                    value={newTitle}
                    placeholder="e.g. Staff Software Engineer"
                    onChange={(e) => setNewTitle(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        addTag('desired_titles', newTitle);
                        setNewTitle('');
                      }
                    }}
                  />
                  <button
                    type="button"
                    className="btn-add-tag"
                    onClick={() => {
                      addTag('desired_titles', newTitle);
                      setNewTitle('');
                    }}
                  >
                    Add
                  </button>
                </div>
                <div className="tags-container">
                  {(profile.desired_titles || []).map((title, i) => (
                    <span key={i} className="interactive-tag">
                      {title}
                      <button
                        type="button"
                        aria-label={`Remove ${title}`}
                        onClick={() => removeTag('desired_titles', i)}
                      >
                        ✕
                      </button>
                    </span>
                  ))}
                  {(profile.desired_titles || []).length === 0 && (
                    <span className="tags-empty-note">No desired roles added yet.</span>
                  )}
                </div>
              </div>

              {/* Skills */}
              <div className="tag-field-group">
                <label>Skills</label>
                <div className="tag-input-row">
                  <input
                    value={newSkill}
                    placeholder="e.g. TypeScript, PostgreSQL, Rust"
                    onChange={(e) => setNewSkill(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        addTag('skills', newSkill);
                        setNewSkill('');
                      }
                    }}
                  />
                  <button
                    type="button"
                    className="btn-add-tag"
                    onClick={() => {
                      addTag('skills', newSkill);
                      setNewSkill('');
                    }}
                  >
                    Add
                  </button>
                </div>
                <div className="tags-container">
                  {(profile.skills || []).map((skill, i) => (
                    <span key={i} className="interactive-tag">
                      {skill}
                      <button
                        type="button"
                        aria-label={`Remove ${skill}`}
                        onClick={() => removeTag('skills', i)}
                      >
                        ✕
                      </button>
                    </span>
                  ))}
                  {(profile.skills || []).length === 0 && (
                    <span className="tags-empty-note">No skills added yet.</span>
                  )}
                </div>
              </div>

              {/* Preferred Locations */}
              <div className="tag-field-group">
                <label>Preferred Locations</label>
                <div className="tag-input-row">
                  <input
                    value={newLoc}
                    placeholder="e.g. San Francisco, Remote, Berlin"
                    onChange={(e) => setNewLoc(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        addTag('preferred_locations', newLoc);
                        setNewLoc('');
                      }
                    }}
                  />
                  <button
                    type="button"
                    className="btn-add-tag"
                    onClick={() => {
                      addTag('preferred_locations', newLoc);
                      setNewLoc('');
                    }}
                  >
                    Add
                  </button>
                </div>
                <div className="tags-container">
                  {(profile.preferred_locations || []).map((loc, i) => (
                    <span key={i} className="interactive-tag">
                      {loc}
                      <button
                        type="button"
                        aria-label={`Remove ${loc}`}
                        onClick={() => removeTag('preferred_locations', i)}
                      >
                        ✕
                      </button>
                    </span>
                  ))}
                </div>
              </div>

              {/* Matching Preferences Toggles */}
              <div className="checkbox-group">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={profile.remote_only ?? false}
                    onChange={(e) => setProfile({ ...profile, remote_only: e.target.checked })}
                  />
                  <span>Only recommend roles explicitly marked Remote</span>
                </label>

                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={profile.use_resume_skills ?? true}
                    onChange={(e) =>
                      setProfile({ ...profile, use_resume_skills: e.target.checked })
                    }
                  />
                  <span>Use keywords detected from your uploaded resume in job matching</span>
                </label>
              </div>

              {(['education', 'experience', 'projects'] as const).map((field) => (
                <label key={field} className="form-field">
                  <span>{field[0].toUpperCase() + field.slice(1)}</span>
                  <textarea
                    className="profile-textarea"
                    rows={4}
                    value={(profile[field] ?? []).join('\n')}
                    onChange={(event) => setProfile({
                      ...profile,
                      [field]: event.target.value.split('\n').slice(0, 30),
                    })}
                  />
                </label>
              ))}
              <fieldset className="candidate-links">
                <legend>Professional links</legend>
                {(profile.links ?? []).map((link, index) => (
                  <div className="candidate-link-row" key={index}>
                    <input aria-label={`Link ${index + 1} label`} value={link.label} required
                      onChange={(event) => setProfile({
                        ...profile,
                        links: profile.links?.map((item, i) => i === index ? { ...item, label: event.target.value } : item),
                      })} />
                    <input aria-label={`Link ${index + 1} URL`} type="url" placeholder="https://" value={link.url} required
                      onChange={(event) => setProfile({
                        ...profile,
                        links: profile.links?.map((item, i) => i === index ? { ...item, url: event.target.value } : item),
                      })} />
                    <button className="btn-secondary" type="button" onClick={() => setProfile({
                      ...profile,
                      links: profile.links?.filter((_, i) => i !== index),
                    })}>Remove link</button>
                  </div>
                ))}
                <button className="btn-secondary" type="button" disabled={(profile.links?.length ?? 0) >= 12}
                  onClick={() => setProfile({ ...profile, links: [...(profile.links ?? []), { label: '', url: '' }] })}>
                  Add LinkedIn, GitHub, portfolio, or other link
                </button>
              </fieldset>
              <div className="form-submit-row">
                <button type="button" className="btn-secondary" disabled={saving} onClick={cancelEditing}>Cancel</button>
                <button type="submit" className="primary" disabled={saving}>
                  {saving ? 'Saving…' : 'Save profile'}
                </button>
              </div>
            </form>}
          </section>

          {/* Right sidebar: Resume upload & Account security */}
          <div className="profile-aside-column">
            <ResumeSection onUseSuggestions={savedProfile.current && !saving ? (resume) => {
              setSaveSuccess(false);
              setEditing(true);
              setProfile((current) => {
                const next = { ...current };
                for (const field of ['full_name', 'headline', 'bio'] as const) {
                  if (!current[field]?.trim() && resume.suggestions?.[field]) {
                    next[field] = resume.suggestions[field];
                  }
                }
                for (const field of ['education', 'experience', 'projects'] as const) {
                  next[field] = [...new Set([...(current[field] ?? []), ...(resume.suggestions?.[field] ?? [])])].slice(0, 30);
                }
                next.skills = [...new Set([...(current.skills ?? []), ...resume.detected_skills])].slice(0, 50);
                const links = new Map((current.links ?? []).map((link) => [link.url, link]));
                for (const link of resume.suggestions?.links ?? []) {
                  if (!links.has(link.url)) links.set(link.url, link);
                }
                next.links = [...links.values()].slice(0, 12);
                return next;
              });
            } : undefined} />

            {/* Account Settings / Password change */}
            <section className="profile-subcard">
              <h3>Account Security</h3>
              <div className="security-form">
                <p>{verified ? 'Email verified' : 'Verify your email address'}</p>
                {!verified && (
                  <>
                    <button type="button" className="btn-secondary" disabled={emailPending}
                      onClick={() => void verifyEmail(false)}>
                      {codeSent ? 'Resend code' : 'Send verification code'}
                    </button>
                    {codeSent && (
                      <form onSubmit={(event) => { event.preventDefault(); void verifyEmail(true); }}>
                        <label>Verification code
                          <input inputMode="numeric" autoComplete="one-time-code" value={code}
                            pattern="[0-9]{8}" maxLength={8} required
                            onChange={(event) => setCode(event.target.value)} />
                        </label>
                        <button type="submit" className="btn-secondary" disabled={emailPending}>Verify email</button>
                      </form>
                    )}
                    {emailNotice && <p role="status">{emailNotice}</p>}
                    {emailError && <p role="alert">{emailError}</p>}
                  </>
                )}
              </div>

            </section>

            {/* Danger Zone: Account Deletion */}
            <section className="profile-subcard danger-card">
              <h3>Delete Account</h3>
              <p className="danger-desc">
                Permanently deletes your live account, saved profile, encrypted resume, and all
                active sessions. This action cannot be undone.
              </p>

              {deleteError && (
                <div className="notice error sub-error" role="alert">
                  {deleteError}
                </div>
              )}

              {showDeleteConfirm ? (
                <form onSubmit={handleDeleteAccount} className="delete-form">
                  <label>
                    Enter your password to confirm deletion:
                    <input
                      type="password"
                      required
                      value={deletePw}
                      onChange={(e) => setDeletePw(e.target.value)}
                    />
                  </label>
                  <div className="delete-action-row">
                    <button type="submit" className="btn-danger-confirm" disabled={deleting}>
                      {deleting ? 'Deleting account…' : 'Permanently delete account'}
                    </button>
                    <button
                      type="button"
                      className="btn-text"
                      onClick={() => setShowDeleteConfirm(false)}
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              ) : (
                <button
                  type="button"
                  className="btn-danger"
                  onClick={() => setShowDeleteConfirm(true)}
                >
                  Delete account…
                </button>
              )}
            </section>
          </div>
        </div>
      )}
    </div>
  );
}

