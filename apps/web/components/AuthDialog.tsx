'use client';

import { FormEvent, useEffect, useState } from 'react';
import { authLogin, authRegister, type AccountOut } from '../lib/api';

interface AuthDialogProps {
  isOpen: boolean;
  initialMode?: 'login' | 'register';
  onClose: () => void;
  onSuccess: (account: AccountOut) => void;
}

export default function AuthDialog({
  isOpen,
  initialMode = 'login',
  onClose,
  onSuccess,
}: AuthDialogProps) {
  const [mode, setMode] = useState<'login' | 'register'>(initialMode);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    setMode(initialMode);
    setError('');
    setPassword('');
  }, [initialMode, isOpen]);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');

    if (password.length < 12) {
      setError('Password must be at least 12 characters.');
      return;
    }
    if (password.length > 128) {
      setError('Password must not exceed 128 characters.');
      return;
    }

    setBusy(true);
    try {
      const account =
        mode === 'register'
          ? await authRegister({ email, password })
          : await authLogin({ email, password });
      setEmail('');
      setPassword('');
      onSuccess(account);
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Authentication failed';
      if (msg.includes('409') || msg.toLowerCase().includes('already exists')) {
        setError('An account with this email already exists.');
      } else if (msg.includes('401') || msg.toLowerCase().includes('invalid')) {
        setError('Invalid email or password.');
      } else if (msg.includes('503') || msg.toLowerCase().includes('not enabled')) {
        setError('Account registration is currently disabled on this deployment.');
      } else if (msg.includes('429')) {
        setError('Too many requests. Please wait a moment before trying again.');
      } else {
        setError(msg);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div
        className="modal-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-dialog-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <div className="modal-tabs" role="tablist">
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'login'}
              className={`modal-tab ${mode === 'login' ? 'active' : ''}`}
              onClick={() => {
                setMode('login');
                setError('');
              }}
            >
              Sign In
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'register'}
              className={`modal-tab ${mode === 'register' ? 'active' : ''}`}
              onClick={() => {
                setMode('register');
                setError('');
              }}
            >
              Create Account
            </button>
          </div>
          <button
            type="button"
            className="modal-close-btn"
            onClick={onClose}
            aria-label="Close dialog"
          >
            ✕
          </button>
        </div>

        <h2 id="auth-dialog-title" className="auth-title">
          {mode === 'login' ? 'Welcome back' : 'Create your account'}
        </h2>
        <p className="auth-sub">
          {mode === 'login'
            ? 'Sign in to access your saved profile, resume, and tailored recommendations.'
            : 'Save your profile and find jobs that match your skills.'}
        </p>

        {error && (
          <div className="notice error auth-error" role="alert">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form">
          <label>
            Email address
            <input
              type="email"
              required
              autoComplete="email"
              maxLength={254}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              disabled={busy}
            />
          </label>

          <label>
            Password
            <input
              type="password"
              required
              autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
              minLength={12}
              maxLength={128}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={mode === 'register' ? 'At least 12 characters' : undefined}
              disabled={busy}
            />
            {mode === 'register' && <small className="field-hint">Use 12 to 128 characters.</small>}
          </label>

          <div className="auth-actions">
            <button type="submit" className="primary auth-submit" disabled={busy}>
              {busy
                ? 'Processing…'
                : mode === 'register'
                ? 'Create account'
                : 'Sign in'}
            </button>
          </div>
        </form>

        <fieldset className="auth-providers" aria-describedby="auth-providers-status">
          <legend>Continue with</legend>
          <div className="auth-provider-options">
            {['Google', 'LinkedIn', 'GitHub'].map((provider) => (
              <button key={provider} type="button" className="btn-secondary" disabled>
                {provider}
              </button>
            ))}
          </div>
          <small id="auth-providers-status">Social sign-in is unavailable in this preview.</small>
        </fieldset>
      </div>
    </div>
  );
}

