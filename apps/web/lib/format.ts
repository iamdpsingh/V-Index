// lib/format.ts — Display-formatting utilities

/**
 * Formats an ISO date-time string as a locale date string.
 * Returns 'Never' for null/empty values.
 */
export function formatDate(value: string | null): string {
  if (!value) return 'Never';
  return new Date(value).toLocaleString();
}

/**
 * Formats an enum-style string to human-readable: lowercase, underscores → spaces.
 */
export function formatLabel(value: string): string {
  return value.toLowerCase().replaceAll('_', ' ');
}

/**
 * Formats a salary object to a human-readable string, or '' if null/empty.
 */
export function formatSalary(salary: Record<string, unknown> | null): string {
  if (!salary) return '';

  const { min, max, currency, period } = salary as {
    min?: unknown;
    max?: unknown;
    currency?: unknown;
    period?: unknown;
  };

  const curr = typeof currency === 'string' ? currency.toUpperCase() : '';
  const per = typeof period === 'string' ? `/${period}` : '';

  if (typeof min === 'number' && typeof max === 'number') {
    return `${curr} ${min.toLocaleString()}–${max.toLocaleString()}${per}`.trim();
  }
  if (typeof min === 'number') {
    return `${curr} ${min.toLocaleString()}+${per}`.trim();
  }
  if (typeof max === 'number') {
    return `Up to ${curr} ${max.toLocaleString()}${per}`.trim();
  }

  // Fallback: join any top-level string/number values
  const parts = Object.entries(salary)
    .filter(([, v]) => typeof v === 'string' || typeof v === 'number')
    .map(([k, v]) => `${k}: ${v}`);

  return parts.join(', ');
}
