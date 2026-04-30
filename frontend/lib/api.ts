export const BACKEND_BASE =
  process.env.NEXT_PUBLIC_BACKEND_BASE_URL ?? "http://localhost:8000";

export function getServerBackendBase() {
  return (
    process.env.BACKEND_BASE_URL ??
    process.env.NEXT_PUBLIC_BACKEND_BASE_URL ??
    "http://localhost:8000"
  );
}

export function getEnvironmentLabel() {
  const explicit = process.env.NEXT_PUBLIC_CONEXUS_ENV?.trim();
  if (explicit) return explicit;
  return BACKEND_BASE.includes("localhost") || BACKEND_BASE.includes("127.0.0.1")
    ? "Local"
    : "Dev";
}

/** Cookie-authenticated admin API calls. On 401, redirects to `/login` in the browser. Do not use for `POST /admin/auth/login` or unauthenticated routes (`/health`, gateway `/v1/...`). */
export async function adminSessionFetch(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  const res = await fetch(input, {
    ...init,
    credentials: init?.credentials ?? "include",
  });
  if (res.status === 401 && typeof window !== "undefined") {
    window.location.href = "/login";
  }
  return res;
}

export async function readJsonSafe(res: Response): Promise<unknown> {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

// ---------------------------------------------------------------------------
// Normalized error type and parser
// ---------------------------------------------------------------------------

export type ApiError = {
  message: string;
  detail?: unknown;
  status?: number;
};

export type AdminResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: ApiError };

/** Normalize any backend error shape into a safe, renderable ApiError. */
export function parseApiError(error: unknown, status?: number): ApiError {
  if (error == null) {
    return { message: "Request failed.", status };
  }
  if (typeof error === "string") {
    return { message: error || "Request failed.", status };
  }
  if (error instanceof Error) {
    return { message: error.message, status };
  }
  if (typeof error === "object") {
    const obj = error as Record<string, unknown>;
    const detail = obj.detail;

    if (typeof detail === "string") {
      return { message: detail, detail, status };
    }
    if (Array.isArray(detail)) {
      // FastAPI validation error array: [{ msg, loc, type }, ...]
      const messages = detail
        .map((item) => {
          if (typeof item === "object" && item !== null) {
            const v = item as Record<string, unknown>;
            const loc = Array.isArray(v.loc) ? v.loc.join(" → ") : "";
            const msg = typeof v.msg === "string" ? v.msg : "";
            return loc ? `${loc}: ${msg}` : msg;
          }
          return String(item);
        })
        .filter(Boolean)
        .join("; ");
      return { message: messages || "Validation error.", detail, status };
    }
    if (detail && typeof detail === "object") {
      const d = detail as Record<string, unknown>;
      if (typeof d.message === "string") {
        return { message: d.message, detail, status };
      }
    }
    // Fallback: stringify the body, but never render secrets
    return { message: "Request failed.", detail: error, status };
  }
  return { message: "Request failed.", status };
}

// ---------------------------------------------------------------------------
// Typed admin API helpers — all paths are relative to BACKEND_BASE
// ---------------------------------------------------------------------------

async function _adminRequest<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<AdminResult<T>> {
  const url = `${BACKEND_BASE}${path}`;
  const init: RequestInit = { method };
  if (body !== undefined) {
    init.headers = { "Content-Type": "application/json" };
    init.body = JSON.stringify(body);
  }
  try {
    const res = await adminSessionFetch(url, init);
    const raw = await readJsonSafe(res);
    if (!res.ok) {
      return { ok: false, error: parseApiError(raw, res.status) };
    }
    return { ok: true, data: raw as T };
  } catch (err) {
    return { ok: false, error: parseApiError(err) };
  }
}

export function getAdminJson<T>(path: string): Promise<AdminResult<T>> {
  return _adminRequest<T>("GET", path);
}

export function postAdminJson<TBody, TResult>(
  path: string,
  body: TBody,
): Promise<AdminResult<TResult>> {
  return _adminRequest<TResult>("POST", path, body);
}

export function putAdminJson<TBody, TResult>(
  path: string,
  body: TBody,
): Promise<AdminResult<TResult>> {
  return _adminRequest<TResult>("PUT", path, body);
}

export function deleteAdminJson<TResult>(path: string): Promise<AdminResult<TResult>> {
  return _adminRequest<TResult>("DELETE", path);
}

// ---------------------------------------------------------------------------
// Legacy helpers — preserved for backward compatibility
// ---------------------------------------------------------------------------

export function formatApiError(error: unknown) {
  if (!error) return "Request failed.";
  if (typeof error === "string") return error;
  if (error instanceof Error) return error.message;
  if (typeof error === "object" && "detail" in error) {
    const detail = (error as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail === "object" && "message" in detail) {
      const message = (detail as { message?: unknown }).message;
      if (typeof message === "string") return message;
    }
    return JSON.stringify(detail, null, 2);
  }
  return JSON.stringify(error, null, 2);
}

export function formatDate(value: string | null | undefined) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}
