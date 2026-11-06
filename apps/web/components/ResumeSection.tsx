'use client';

import { ChangeEvent, useEffect, useState } from 'react';
import {
  deleteResume,
  downloadResume,
  getResume,
  uploadResume,
  type ResumeOut,
} from '../lib/api';
import { formatDate } from '../lib/format';

interface ResumeSectionProps {
  onSkillsUpdated?: () => void;
}

export default function ResumeSection({ onSkillsUpdated }: ResumeSectionProps) {
  const [resume, setResume] = useState<ResumeOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [successNotice, setSuccessNotice] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState(false);

  useEffect(() => {
    loadResume();
  }, []);

  async function loadResume() {
    setLoading(true);
    setError('');
    try {
      const data = await getResume();
      setResume(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load resume';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  async function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    // Reset file input so re-selecting the same file works if needed
    e.target.value = '';

    // Bounded client check before sending
    if (file.size > 5 * 1024 * 1024) {
      setError('File size exceeds the 5 MiB limit.');
      return;
    }

    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!ext || !['pdf', 'docx', 'txt'].includes(ext)) {
      setError('Supported formats are PDF, DOCX, and UTF-8 TXT only.');
      return;
    }

    setUploading(true);
    setError('');
    setSuccessNotice('');

    try {
      const uploaded = await uploadResume(file);
      setResume(uploaded);
      setSuccessNotice(`Resume "${uploaded.filename}" processed and saved successfully.`);
      if (onSkillsUpdated) onSkillsUpdated();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Upload failed';
      // Prior resume remains visible if replacement fails
      if (msg.includes('413')) {
        setError('Resume exceeds 5 MiB size limit.');
      } else if (msg.includes('415')) {
        setError('Unsupported format. Supported resume types are readable PDF, DOCX, and UTF-8 TXT.');
      } else if (msg.includes('422')) {
        setError(
          'Could not parse resume text. Scanned images, encrypted/password-protected files, and active macros are not supported.'
        );
      } else if (msg.includes('503')) {
        setError('Resume processing service is temporarily unavailable.');
      } else {
        setError(msg);
      }
    } finally {
      setUploading(false);
    }
  }

  async function handleDownload() {
    try {
      const { blob, filename } = await downloadResume();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename || resume?.filename || 'resume';
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Download failed');
    }
  }

  async function handleDelete() {
    try {
      await deleteResume();
      setResume(null);
      setDeleteConfirm(false);
      setSuccessNotice('Saved resume and extracted keywords removed.');
      if (onSkillsUpdated) onSkillsUpdated();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Delete failed');
    }
  }

  return (
    <div className="resume-section">
      <div className="section-header">
        <h3>Resume Document</h3>
        <p className="section-desc">
          Upload a readable PDF, DOCX, or TXT file (up to 5 MiB). Authenticated encryption in
          database; text parsed locally for professional keyword matching.
        </p>
      </div>

      {error && (
        <div className="notice error resume-error" role="alert">
          {error}
        </div>
      )}

      {successNotice && (
        <div className="notice success-notice" role="status">
          {successNotice}
        </div>
      )}

      {loading ? (
        <div className="loading-state">Checking saved resume…</div>
      ) : resume ? (
        <div className="resume-card">
          <div className="resume-main">
            <div className="resume-icon" aria-hidden="true">
              📄
            </div>
            <div className="resume-meta">
              <h4 className="resume-filename">{resume.filename}</h4>
              <p className="resume-details">
                {(resume.size_bytes / 1024).toFixed(1)} KB · {resume.media_type} · updated{' '}
                {formatDate(resume.updated_at)}
              </p>
            </div>
            <div className="resume-actions">
              <button
                type="button"
                className="btn-secondary"
                onClick={handleDownload}
                title="Download original file"
              >
                Download ↓
              </button>
              {deleteConfirm ? (
                <div className="delete-confirm-group">
                  <span className="confirm-prompt">Remove file?</span>
                  <button type="button" className="btn-danger-confirm" onClick={handleDelete}>
                    Yes, remove
                  </button>
                  <button
                    type="button"
                    className="btn-text"
                    onClick={() => setDeleteConfirm(false)}
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  className="btn-danger"
                  onClick={() => setDeleteConfirm(true)}
                  title="Delete saved resume"
                >
                  Remove ✕
                </button>
              )}
            </div>
          </div>

          {/* Extracted professional terms */}
          <div className="resume-skills-block">
            <span className="skills-label">Detected keywords ({resume.detected_skills.length}):</span>
            {resume.detected_skills.length > 0 ? (
              <div className="skill-chips">
                {resume.detected_skills.map((skill) => (
                  <span key={skill} className="skill-chip">
                    {skill}
                  </span>
                ))}
              </div>
            ) : (
              <p className="skills-empty">No recognizable professional terms detected in document text.</p>
            )}
          </div>

          {/* Replace file control */}
          <div className="resume-replace-bar">
            <label className="file-upload-label">
              <span>{uploading ? 'Processing replacement…' : 'Replace resume file…'}</span>
              <input
                type="file"
                accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
                onChange={handleFileChange}
                disabled={uploading}
                className="hidden-file-input"
              />
            </label>
            <small className="replace-hint">
              If an upload is rejected, your current resume is retained.
            </small>
          </div>
        </div>
      ) : (
        <div className="resume-empty-dropzone">
          <label className="dropzone-label">
            <span className="dropzone-icon" aria-hidden="true">
              ☁
            </span>
            <span className="dropzone-title">
              {uploading ? 'Extracting and encrypting…' : 'Choose a resume to upload'}
            </span>
            <span className="dropzone-sub">PDF, DOCX, or UTF-8 TXT up to 5 MiB</span>
            <input
              type="file"
              accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
              onChange={handleFileChange}
              disabled={uploading}
              className="hidden-file-input"
            />
          </label>
        </div>
      )}

      <div className="parser-disclaimer">
        <small>
          Deterministic bounded extraction: 20 PDF pages, 100k character budget. No OCR, external AI
          models, or third-party APIs are used. Password-protected files or image scans are
          rejected.
        </small>
      </div>
    </div>
  );
}

