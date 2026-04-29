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

export async function readJsonSafe(res: Response): Promise<unknown> {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

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
