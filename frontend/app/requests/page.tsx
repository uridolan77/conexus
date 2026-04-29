export default function RequestsPage() {
  return (
    <>
      <h2>Requests</h2>
      <p className="muted">
        Request monitoring lands in M5. The M2 gateway will start writing rows
        first, and this view will surface them.
      </p>
      <div className="card">
        <h3>Coming in M5</h3>
        <ul>
          <li>request list with filters</li>
          <li>request detail with provider response and error</li>
          <li>basic dashboard cards (success rate, latency, cost)</li>
        </ul>
      </div>
    </>
  );
}
