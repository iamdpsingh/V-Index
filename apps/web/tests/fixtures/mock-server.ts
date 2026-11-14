import { Page } from '@playwright/test';

export type MockJobs = { total: number; limit: number; offset: number; items: MockJob[] };
export type MockJob = {
  id: number; external_id: string; title: string; company: string;
  description: string; quality_flags?: string[]; location: string; source_url: string; application_url: string;
  employment_type: string | null; remote_status: string | null;
  salary: null; published_at: string | null;
  first_seen_at: string; last_changed_at: string;
  sources: MockSource[];
};
export type MockSource = {
  source_id: number; source_url: string; application_url: string;
  status: string; last_checked_at: string;
};
export type MockProvider = {
  name: string; kind: string; implementation_status: string; evidence_status: string;
  extraction_count: number | null; last_run_at: string | null;
  limitations: string[]; failure_reason: string | null;
};
export type MockSourceOut = {
  id: number; provider: string; slug: string; company: string;
  url: string; refresh_minutes: number; next_check: string; failures: number;
};
export type MockRunOut = {
  id: number; source_id: number; started_at: string; finished_at: string | null;
  status: string; count: number; error: string | null;
};

export const SAMPLE_JOB: MockJob = {
  id: 1, external_id: 'ext-1',
  title: 'Senior Engineer', company: 'Acme Corp',
  description: 'A great role with interesting problems.',
  quality_flags: [],
  location: 'Remote — Global',
  source_url: 'https://boards.greenhouse.io/acme/jobs/1',
  application_url: 'https://boards.greenhouse.io/acme/jobs/1',
  employment_type: 'Full-time', remote_status: 'Remote',
  salary: null, published_at: '2026-10-01T00:00:00Z',
  first_seen_at: '2026-10-01T00:00:00Z', last_changed_at: '2026-10-01T00:00:00Z',
  sources: [{
    source_id: 1,
    source_url: 'https://boards.greenhouse.io/acme/jobs/1',
    application_url: 'https://boards.greenhouse.io/acme/jobs/1',
    status: 'ACTIVE', last_checked_at: '2026-10-01T12:00:00Z',
  }],
};

export const LONG_JOB: MockJob = {
  ...SAMPLE_JOB, id: 2, external_id: 'ext-2',
  title: 'Staff Engineer with an Exceptionally Long Job Title That Wraps on Mobile',
  location: 'San Francisco, California, United States of America (Hybrid — 3 days on site per week)',
  description: 'A'.repeat(2000),
  employment_type: null, remote_status: null,
};

export const SAMPLE_PROVIDERS: MockProvider[] = [
  { name: 'Greenhouse', kind: 'ats', implementation_status: 'IMPLEMENTED', evidence_status: 'LIVE_VERIFIED', extraction_count: 150, last_run_at: '2026-10-01T00:00:00Z', limitations: [], failure_reason: null },
  { name: 'Lever', kind: 'ats', implementation_status: 'IMPLEMENTED', evidence_status: 'LIVE_VERIFIED', extraction_count: 80, last_run_at: '2026-10-01T00:00:00Z', limitations: ['No salary data'], failure_reason: null },
  { name: 'Ashby', kind: 'ats', implementation_status: 'IMPLEMENTED', evidence_status: 'NOT_VERIFIED', extraction_count: null, last_run_at: null, limitations: [], failure_reason: null },
  { name: 'Workday', kind: 'ats', implementation_status: 'NOT_STARTED', evidence_status: 'NOT_VERIFIED', extraction_count: null, last_run_at: null, limitations: ['Tenant-specific URLs'], failure_reason: null },
  { name: 'iCIMS', kind: 'ats', implementation_status: 'NOT_STARTED', evidence_status: 'NOT_VERIFIED', extraction_count: null, last_run_at: null, limitations: [], failure_reason: 'Requires API key' },
];

export const SAMPLE_SOURCE_OUT: MockSourceOut = {
  id: 1, provider: 'greenhouse', slug: 'acme', company: 'Acme Corp',
  url: 'https://boards.greenhouse.io/acme', refresh_minutes: 360,
  next_check: '2026-10-01T06:00:00Z', failures: 0,
};

export const SAMPLE_RUN_OUT: MockRunOut = {
  id: 1, source_id: 1, started_at: '2026-10-01T00:00:00Z',
  finished_at: '2026-10-01T00:05:00Z', status: 'SUCCESS', count: 150, error: null,
};

export const SAMPLE_ACCOUNT = {
  id: 'acc-1',
  email: 'alex@example.com',
  email_verified: false,
  created_at: '2026-10-01T00:00:00Z',
};

export const SAMPLE_PROFILE = {
  full_name: 'Alex Morgan',
  headline: 'Senior Systems Engineer',
  location: 'London, UK',
  bio: 'Distributed systems builder with passion for robust architecture.',
  desired_titles: ['Systems Engineer', 'Backend Lead'],
  skills: ['Python', 'PostgreSQL', 'Docker'],
  preferred_locations: ['London', 'Remote'],
  remote_only: false,
  experience_years: 6,
  updated_at: '2026-10-01T12:00:00Z',
};

export const SAMPLE_RESUME = {
  filename: 'alex_morgan_cv.pdf',
  media_type: 'application/pdf',
  size_bytes: 42000,
  updated_at: '2026-10-01T12:00:00Z',
};

export const SAMPLE_RECOMMENDATIONS = {
  items: [
    {
      job: SAMPLE_JOB,
      rank_score: 10,
      reasons: ['Matches desired role: Engineer', 'Matches skill: Python'],
    },
  ],
  total_candidates: 1,
  candidates_ranked: 1,
  candidate_limit: 1000,
  truncated: false,
  limit: 20,
  offset: 0,
  needs_preferences: false,
};

export async function mockProviders(page: Page, providers = SAMPLE_PROVIDERS) {
  await page.route('**/api/v1/providers', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(providers) });
  });
}

export async function mockJobs(page: Page, jobs: MockJobs) {
  await page.route('**/api/v1/jobs**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(jobs) });
  });
}

export async function mockJobsEmpty(page: Page) {
  await mockJobs(page, { total: 0, limit: 25, offset: 0, items: [] });
}

export async function mockSources(page: Page, sources = [SAMPLE_SOURCE_OUT], runs = [SAMPLE_RUN_OUT]) {
  await page.route('**/api/v1/sources', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(sources) });
    } else {
      await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(SAMPLE_SOURCE_OUT) });
    }
  });
  await page.route('**/api/v1/runs**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(runs) });
  });
}

export async function mockSourceError(page: Page, status: number, detail: string) {
  await page.route('**/api/v1/sources', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify({ detail }) });
    } else {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    }
  });
}

export async function mockRefreshError(page: Page, status: number, detail: string) {
  await page.route('**/api/v1/sources/*/refresh', async (route) => {
    await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify({ detail }) });
  });
}

export async function mockAuth(page: Page, account: typeof SAMPLE_ACCOUNT | null = SAMPLE_ACCOUNT) {
  await page.route('**/api/v1/me', async (route) => {
    if (route.request().method() === 'GET') {
      if (account) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(account) });
      } else {
        await route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Authentication required' }) });
      }
    } else if (route.request().method() === 'DELETE') {
      await route.fulfill({ status: 204 });
    }
  });

  await page.route('**/api/v1/auth/login', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(account || SAMPLE_ACCOUNT) });
  });

  await page.route('**/api/v1/auth/register', async (route) => {
    await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(account || SAMPLE_ACCOUNT) });
  });

  await page.route('**/api/v1/auth/logout', async (route) => {
    await route.fulfill({ status: 204 });
  });
}

export async function mockProfile(page: Page, profile: typeof SAMPLE_PROFILE = SAMPLE_PROFILE) {
  await page.route('**/api/v1/me/profile', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(profile) });
    } else {
      const data = route.request().postDataJSON();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ...profile, ...data, updated_at: new Date().toISOString() }),
      });
    }
  });
}

export async function mockResume(page: Page, resume: typeof SAMPLE_RESUME | null = SAMPLE_RESUME) {
  await page.route('**/api/v1/me/resume', async (route) => {
    if (route.request().method() === 'GET') {
      if (resume) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(resume) });
      } else {
        await route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'No resume saved' }) });
      }
    } else if (route.request().method() === 'DELETE') {
      await route.fulfill({ status: 204 });
    } else if (route.request().method() === 'PUT') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(resume || SAMPLE_RESUME),
      });
    }
  });
}

export async function mockRecommendations(
  page: Page,
  recs: typeof SAMPLE_RECOMMENDATIONS = SAMPLE_RECOMMENDATIONS
) {
  await page.route('**/api/v1/me/recommendations**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(recs) });
  });
}
