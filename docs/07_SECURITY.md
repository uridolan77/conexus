# 07 — Security notes (BO + backend)

## CSRF posture (admin cookie auth)

Conexus BO authentication uses a cookie-backed session (`conexus_admin_session`) sent with `credentials: "include"`.

**Current posture**:

- The backend sets cookies with `SameSite=Lax` by default (see `[docs/06_DEPLOYMENT.md](06_DEPLOYMENT.md)`).
- Many deployments use `bo.<domain>` (frontend) and `api.<domain>` (backend); these are typically **same-site**, so `SameSite=Lax` cookies are sent for same-site POST requests.

**Policy**:

- **State-changing admin endpoints must not be implemented as `GET`.**
- Prefer `POST/PUT/PATCH/DELETE` for mutations, and keep `GET` read-only.

If Conexus is deployed in a cross-site context (or you explicitly set `COOKIE_SAMESITE=none`), consider adding a CSRF token mechanism (e.g. double-submit tokens) before exposing admin endpoints broadly.

