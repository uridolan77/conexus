const DASH = "—";

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return DASH;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function formatCost(value: number | null | undefined): string {
  if (value == null) return DASH;
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 4,
  }).format(value);
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null) return DASH;
  return `${value.toFixed(0)}%`;
}

export function formatTokens(value: number | null | undefined): string {
  if (value == null) return DASH;
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(value);
}

export function formatLatency(ms: number | null | undefined): string {
  if (ms == null) return DASH;
  if (ms < 1) return "<1ms";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function formatNullable(value: unknown, fallback = DASH): string {
  if (value == null) return fallback;
  const s = String(value);
  return s === "" ? fallback : s;
}

export function formatDurationSeconds(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return s > 0 ? `${h}h ${m}m ${s}s` : `${h}h ${m}m`;
  return `${m}m ${s}s`;
}

/** Compute percentage of current/limit, capped at 999. Returns null when limit is absent. */
export function computePercent(current: number, limit: number | null | undefined): number | null {
  if (!limit || limit <= 0) return null;
  return Math.min(999, (current / limit) * 100);
}
