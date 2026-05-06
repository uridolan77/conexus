from __future__ import annotations

from app.main import app


def test_admin_mutation_endpoints_are_not_get() -> None:
    """Guardrail: state-changing admin endpoints must not be GET.

    This isn't a full CSRF solution; it's a cheap regression check that keeps
    obvious mistakes out of the API surface.
    """

    forbidden_get_paths = {
        "/admin/auth/logout",
        "/admin/auth/login",
    }

    routes = getattr(app, "routes", [])
    for r in routes:
        path = getattr(r, "path", None)
        methods = getattr(r, "methods", None)
        if not path or not methods:
            continue
        if path in forbidden_get_paths:
            assert "GET" not in methods, f"{path} must not allow GET (methods={sorted(methods)})"

