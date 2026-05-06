const SENSITIVE_KEY_RE =
  /api_?key|apikey|token|secret|password|authorization|bearer|^key$/i;

const REDACTED = "[REDACTED]";

function isSensitiveKey(key: string): boolean {
  return SENSITIVE_KEY_RE.test(key);
}

/**
 * Deep-walk an object and replace values for keys that look sensitive
 * (api_key, token, secret, password, authorization, bearer, key) with [REDACTED].
 * Non-object primitives and arrays are returned as-is (arrays are recursed into).
 * Handles cycles via WeakMap.
 */
export function redactSensitiveObject(value: unknown): unknown {
  const seen = new WeakMap<object, unknown>();

  function visit(v: unknown): unknown {
    if (v == null || typeof v !== "object") return v;

    const obj = v as object;
    const cached = seen.get(obj);
    if (cached !== undefined) return cached;

    if (Array.isArray(v)) {
      const out: unknown[] = [];
      seen.set(obj, out);
      for (const item of v) out.push(visit(item));
      return out;
    }

    const rec = v as Record<string, unknown>;
    const out: Record<string, unknown> = {};
    seen.set(obj, out);
    for (const [k, val] of Object.entries(rec)) {
      out[k] = isSensitiveKey(k) ? REDACTED : visit(val);
    }
    return out;
  }

  try {
    return visit(value);
  } catch {
    return value;
  }
}

/**
 * Conservatively redact obvious bearer token or api key patterns from a string.
 * Replaces `Bearer <token>` and `sk-...` / `cnx_...` style key literals.
 */
export function redactSensitiveString(value: string): string {
  return value
    .replace(/Bearer\s+[^\s"',)]+/gi, `Bearer ${REDACTED}`)
    .replace(/\b(sk-[A-Za-z0-9_-]{8,})/g, REDACTED)
    .replace(/\b(sk-ant-[A-Za-z0-9_-]{8,})/g, REDACTED)
    .replace(/\b(cnx_[A-Za-z0-9_-]{8,})/g, REDACTED)
    .replace(/\b(eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9._-]{10,}\.[A-Za-z0-9._-]{10,})/g, REDACTED);
}
