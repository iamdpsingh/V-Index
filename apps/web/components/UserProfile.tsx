'use client';

import { FormEvent, useEffect, useState } from 'react';
import {
  changePassword,
  deleteAccount,
  getProfile,
  updateProfile,
  type AccountOut,
  type ProfileInput,
} from '../lib/api';
import ResumeSection from './ResumeSection';

interface UserProfileProps {
  account: AccountOut;
  onLogout: () => void;
  onAccountDeleted: () => void;
}

export default function UserProfile({
  account,
  onLogout,
  onAccountDeleted,
}: UserProfileProps) {
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

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [error, setError] = useState('');

  // Tag inputs state
  const [newTitle, setNewTitle] = useState('');
  const [newSkill, setNewSkill] = useState('');
  const [newLoc, setNewLoc] = useState('');

  // Password change state
  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [pwSaving, setPwSaving] = useState(false);
  const [pwSuccess, setPwSuccess] = useState(false);
  const [pwError, setPwError] = useState('');

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
      setProfile({
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
      });
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
      setProfile({
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
      });
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

  async function handleChangePassword(e: FormEvent) {
    e.preventDefault();
    setPwError('');
    setPwSuccess(false);

    if (newPw.length < 12) {
      setPwError('New password must be at least 12 characters.');
      return;
    }

    setPwSaving(true);
    try {
      await changePassword({ password: currentPw, new_password: newPw });
      setPwSuccess(true);
      setCurrentPw('');
      setNewPw('');
      setTimeout(() => setPwSuccess(false), 4000);
    } catch (err: unknown) {
      setPwError(err instanceof Error ? err.message : 'Password change failed');
    } finally {
      setPwSaving(false);
    }
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
        <div className="identity-info">
          <span className="identity-email">{account.email}</span>
          <span className="identity-meta">
            Joined {new Date(account.created_at).toLocaleDateString()} · Private profile
          </span>
        </div>
        <button type="button" className="btn-secondary logout-btn" onClick={onLogout}>
          Sign Out
        </button>
      </div>

      {loading ? (
        <div className="loading-state">Loading your profile…</div>
      ) : (
        <div className="profile-grid">
          {/* Main profile form */}
          <section className="profile-card">
            <h2>Job-Seeker Profile</h2>
            <p className="card-sub">
              Your preferences drive recommendations on the <strong>For You</strong> tab. Signals are
              matched using transparent keyword matching; no data is shared externally.
            </p>

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

            <form onSubmit={handleSaveProfile} className="profile-form">
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
                  <small className="field-hint">Note: Stored in profile; currently not used in ranking.</small>
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
                <label>Desired Job Titles (matches weigh 7× in recommendations)</label>
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
                <label>Skills & Technologies (matches weigh 3× in recommendations)</label>
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

              <div className="form-submit-row">
                <button type="submit" className="primary" disabled={saving}>
                  {saving ? 'Saving…' : 'Save profile'}
                </button>
              </div>
            </form>
          </section>

          {/* Right sidebar: Resume upload & Account security */}
          <div className="profile-aside-column">
            <ResumeSection />

            {/* Account Settings / Password change */}
            <section className="profile-subcard">
              <h3>Account Security</h3>
              <form onSubmit={handleChangePassword} className="security-form">
                {pwError && (
                  <div className="notice error sub-error" role="alert">
                    {pwError}
                  </div>
                )}
                {pwSuccess && (
                  <div className="notice success-notice" role="status">
                    Password updated. Prior sessions rotated.
                  </div>
                )}
                <label>
                  Current password
                  <input
                    type="password"
                    required
                    value={currentPw}
                    onChange={(e) => setCurrentPw(e.target.value)}
                  />
                </label>
                <label>
                  New password (min 12 chars)
                  <input
                    type="password"
                    required
                    minLength={12}
                    maxLength={128}
                    value={newPw}
                    onChange={(e) => setNewPw(e.target.value)}
                  />
                </label>
                <button type="submit" className="btn-secondary" disabled={pwSaving}>
                  {pwSaving ? 'Updating…' : 'Update password'}
                </button>
              </form>
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

