async function fetchHealth(): Promise<{ status: string } | null> {
  const base = process.env.NEXT_PUBLIC_BACKEND_BASE_URL ?? "http://localhost:8000";
  try {
    const res = await fetch(`${base}/health`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as { status: string };
  } catch {
    return null;
  }
}

export async function HealthCard() {
  const health = await fetchHealth();
  return (
    <div className="card">
      <h3>Backend health</h3>
      {health ? (
        <p>
          Status: <strong>{health.status}</strong>
        </p>
      ) : (
        <p className="muted">Backend not reachable.</p>
      )}
    </div>
  );
}
