import { HealthCard } from "../components/HealthCard";

export default function DashboardPage() {
  return (
    <>
      <h2>Dashboard</h2>
      <p className="muted">
        First-deployment shell. Real metrics come online with M2 (gateway) and
        M5 (request monitoring).
      </p>
      <HealthCard />
      <div className="card">
        <h3>Status</h3>
        <dl className="kv">
          <dt>Milestone</dt>
          <dd>M0 — blank repo boots</dd>
          <dt>Next</dt>
          <dd>M2 — first real gateway call</dd>
        </dl>
      </div>
    </>
  );
}
