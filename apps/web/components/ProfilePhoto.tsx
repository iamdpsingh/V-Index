'use client';

import { useEffect, useRef, useState } from 'react';

const endpoint = '/api/v1/me/profile/photo';

export default function ProfilePhoto() {
  const [photo, setPhoto] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const currentUrl = useRef('');
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch(endpoint, { cache: 'no-store', signal: controller.signal })
      .then(async (response) => {
        if (response.status === 404) return;
        if (!response.ok) throw new Error('Could not load your photo.');
        const blob = await response.blob();
        if (controller.signal.aborted) return;
        currentUrl.current = URL.createObjectURL(blob);
        setPhoto(currentUrl.current);
      })
      .catch(() => {
        if (!controller.signal.aborted) setError('Could not load your photo.');
      });
    return () => {
      controller.abort();
      URL.revokeObjectURL(currentUrl.current);
    };
  }, []);

  async function change(file?: File) {
    setError('');
    if (file && file.size > 2 * 1024 * 1024) {
      setError('Choose a photo within 2 MB.');
      return;
    }
    setBusy(true);
    try {
      const response = await fetch(endpoint, { method: file ? 'PUT' : 'DELETE', body: file });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || 'Could not update your photo.');
      }
      URL.revokeObjectURL(currentUrl.current);
      currentUrl.current = '';
      if (file) {
        const image = await fetch(endpoint, { cache: 'no-store' });
        if (!image.ok) throw new Error('Photo saved. Reload to view it.');
        currentUrl.current = URL.createObjectURL(await image.blob());
      }
      setPhoto(currentUrl.current);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not update your photo.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="profile-photo">
      {photo ? <img src={photo} alt="Your profile photo" width={72} height={72} /> : null}
      <div>
        <input ref={input} type="file" hidden aria-label="Profile photo"
          accept="image/jpeg,image/png,image/webp"
          onChange={(event) => {
            const file = event.target.files?.[0];
            event.target.value = '';
            if (file) void change(file);
          }} />
        <button type="button" className="btn-secondary" disabled={busy} onClick={() => input.current?.click()}>
          {photo ? 'Replace photo' : 'Add profile photo'}
        </button>
        {photo && <button type="button" className="btn-secondary" disabled={busy} onClick={() => void change()}>Remove photo</button>}
        <small>Private · JPEG, PNG, or WebP · 2 MB max</small>
        {error && <p role="alert">{error}</p>}
      </div>
    </div>
  );
}
