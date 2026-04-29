"use client";

import { FormEvent, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Field,
  Input,
  PageHeader,
} from "@/components/ui";
import { BACKEND_BASE } from "@/lib/api";

export default function LoginPage() {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${BACKEND_BASE}/admin/auth/login`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
        setError("Invalid credentials.");
        return;
      }
      window.location.href = "/";
    } catch {
      setError("Backend not reachable.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <Card className="auth-card">
        <PageHeader
          eyebrow="Conexus"
          title="Admin login"
          description="Sign in to manage upstream providers, project API keys, smoke tests, and gateway operations."
        />
        <form className="stack" onSubmit={onSubmit}>
          <Field label="Username">
            <Input
              value={username}
              autoComplete="username"
              onChange={(e) => setUsername(e.target.value)}
            />
          </Field>
          <Field label="Password">
            <Input
              type="password"
              value={password}
              autoComplete="current-password"
              onChange={(e) => setPassword(e.target.value)}
            />
          </Field>
          <Button type="submit" disabled={loading}>
            {loading ? "Signing in..." : "Sign in"}
          </Button>
        </form>
        {error && <Alert tone="danger">{error}</Alert>}
      </Card>
    </div>
  );
}
