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

/**
 * Typed fetch helper for the V-Index API.
 * Uses same-origin /api/v1/ (proxied via Next.js rewrite to API_INTERNAL_URL).
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
    ...init,
    headers,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = typeof body.detail === 'string' ? body.detail : '';
    throw new Error(
      detail ? `${detail} (${response.status})` : `Request failed (${response.status})`
    );
  }

  return response.json() as Promise<T>;
}
