// lib/api.ts — OpenAPI-derived TypeScript types and fetch helper

export type ProvenanceOut = {
  source_id: number;
  source_url: string;
  application_url: string;
  status: string;
  last_checked_at: string; // date-time
};

export type JobOut = {
  id: number;
  external_id: string;
  title: string;
  company: string;
  description: string;
  quality_flags?: string[];
  location: string;
  source_url: string;
  application_url: string;
  employment_type: string | null;
  remote_status: string | null;
  salary: Record<string, unknown> | null;
  published_at: string | null; // date-time
  first_seen_at: string; // date-time
  last_changed_at: string; // date-time
  sources: ProvenanceOut[];
};

export type SearchOut = {
  total: number;
  limit: number;
  offset: number;
  items: JobOut[];
};

export type SourceCreate = {
  url: string;
  company: string;
  refresh_minutes?: number; // default 360, min 60, max 10080
};

export type SourceOut = {
  id: number;
  provider: string;
  slug: string;
  company: string;
  url: string;
  refresh_minutes: number;
  next_check: string; // date-time
  failures: number;
};

export type RunOut = {
  id: number;
  source_id: number;
  started_at: string; // date-time
  finished_at: string | null; // date-time
  status: string;
  count: number;
  error: string | null;
};

export type Provider = {
  name: string;
  kind: string;
  implementation_status: string;
  evidence_status: string;
  extraction_count: number | null;
  last_run_at: string | null; // date-time
  limitations: string[];
  failure_reason: string | null;
};

// Private Account, Profile, Resume & Recommendation Types
export type AccountOut = {
  id: string;
  email: string;
  email_verified: boolean;
  created_at: string;
};

export type Credentials = {
  email: string;
  password: string;
};

export type PasswordChange = {
  password: string;
  new_password: string;
};

export type PasswordConfirmation = {
  password: string;
};

export type ProfileInput = {
  full_name?: string;
  headline?: string;
  location?: string;
  bio?: string;
  desired_titles?: string[];
  skills?: string[];
  preferred_locations?: string[];
  remote_only?: boolean;
  use_resume_skills?: boolean;
  experience_years?: number | null;
};

export type ProfileOut = {
  full_name: string;
  headline: string;
  location: string;
  bio: string;
  desired_titles: string[];
  skills: string[];
  preferred_locations: string[];
  remote_only: boolean;
  use_resume_skills: boolean;
  experience_years: number | null;
  updated_at: string | null;
};

export type ResumeOut = {
  filename: string;
  media_type: string;
  size_bytes: number;
  text_characters: number;
  detected_skills: string[];
  updated_at: string;
};

export type RecommendationItem = {
  job: JobOut;
  rank_score: number;
  reasons: string[];
};

export type RecommendationsOut = {
  items: RecommendationItem[];
  total_candidates: number;
  candidates_ranked: number;
  candidate_limit: number;
  truncated: boolean;
  limit: number;
  offset: number;
  needs_preferences: boolean;
  method?: string;
};

/**
 * Typed fetch helper for the V-Index API.
 * Uses same-origin /api/v1/ (proxied via Next.js rewrite to API_INTERNAL_URL).
 * Passes credentials: 'include' for HttpOnly session cookie persistence.
 */
export async function apiFetch<T>(
  path: string,
  token = '',
  init: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(init.headers as Record<string, string> | undefined),
  };

  const response = await fetch(`/api/v1/${path}`, {
    credentials: 'include',
    ...init,
    headers,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    let detail = '';
    if (typeof body.detail === 'string') {
      detail = body.detail;
    } else if (Array.isArray(body.detail) && body.detail[0]?.msg) {
      detail = body.detail[0].msg;
    }
    throw new Error(
      detail ? `${detail} (${response.status})` : `Request failed (${response.status})`
    );
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as unknown as T;
  }

  return response.json() as Promise<T>;
}

// Account & Auth API methods
export async function authRegister(creds: Credentials): Promise<AccountOut> {
  return apiFetch<AccountOut>('auth/register', '', {
    method: 'POST',
    body: JSON.stringify(creds),
  });
}

export async function authLogin(creds: Credentials): Promise<AccountOut> {
  return apiFetch<AccountOut>('auth/login', '', {
    method: 'POST',
    body: JSON.stringify(creds),
  });
}

export async function authLogout(): Promise<void> {
  return apiFetch<void>('auth/logout', '', {
    method: 'POST',
  });
}

export async function getMe(): Promise<AccountOut | null> {
  try {
    return await apiFetch<AccountOut>('me');
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : '';
    if (
      message.includes('(401)') ||
      message.includes('(403)') ||
      message.includes('(404)')
    ) {
      return null;
    }
    throw err;
  }
}

export async function changePassword(body: PasswordChange): Promise<void> {
  return apiFetch<void>('me/password', '', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export async function deleteAccount(body: PasswordConfirmation): Promise<void> {
  return apiFetch<void>('me', '', {
    method: 'DELETE',
    body: JSON.stringify(body),
  });
}

// Profile API methods
export async function getProfile(): Promise<ProfileOut> {
  return apiFetch<ProfileOut>('me/profile');
}

export async function updateProfile(data: ProfileInput): Promise<ProfileOut> {
  return apiFetch<ProfileOut>('me/profile', '', {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

// Resume API methods
export async function getResume(): Promise<ResumeOut | null> {
  try {
    return await apiFetch<ResumeOut>('me/resume');
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : '';
    if (message.includes('(404)')) {
      return null;
    }
    throw err;
  }
}

export async function uploadResume(file: File): Promise<ResumeOut> {
  const response = await fetch('/api/v1/me/resume', {
    method: 'PUT',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/octet-stream',
      'X-Filename': encodeURIComponent(file.name),
    },
    body: file,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    let detail = '';
    if (typeof body.detail === 'string') {
      detail = body.detail;
    } else if (Array.isArray(body.detail) && body.detail[0]?.msg) {
      detail = body.detail[0].msg;
    }
    throw new Error(
      detail ? `${detail} (${response.status})` : `Resume upload failed (${response.status})`
    );
  }

  return response.json() as Promise<ResumeOut>;
}

export async function downloadResume(): Promise<{ blob: Blob; filename?: string }> {
  const response = await fetch('/api/v1/me/resume/download', {
    method: 'GET',
    credentials: 'include',
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = typeof body.detail === 'string' ? body.detail : '';
    throw new Error(
      detail ? `${detail} (${response.status})` : `Download failed (${response.status})`
    );
  }

  // Extract filename from Content-Disposition if present
  let filename: string | undefined;
  const disposition = response.headers.get('Content-Disposition');
  if (disposition) {
    const match = /filename\*?=['"]?(?:UTF-\d['"]*)?([^;\r\n"']*)['"]?/i.exec(disposition);
    if (match && match[1]) {
      filename = decodeURIComponent(match[1]);
    }
  }

  const blob = await response.blob();
  return { blob, filename };
}

export async function deleteResume(): Promise<void> {
  return apiFetch<void>('me/resume', '', {
    method: 'DELETE',
  });
}

// Recommendations API methods
export async function getRecommendations(
  params: { limit?: number; offset?: number } = {}
): Promise<RecommendationsOut> {
  const query = new URLSearchParams();
  if (params.limit !== undefined) query.set('limit', String(params.limit));
  if (params.offset !== undefined) query.set('offset', String(params.offset));
  const qs = query.toString();
  return apiFetch<RecommendationsOut>(`me/recommendations${qs ? `?${qs}` : ''}`);
}
