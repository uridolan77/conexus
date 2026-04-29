export default function ProjectsPage() {
  return (
    <>
      <h2>Projects</h2>
      <p className="muted">
        Projects and API keys land in M4. This shell page is here so the nav
        works on the M0 deploy.
      </p>
      <div className="card">
        <h3>Coming in M4</h3>
        <ul>
          <li>create project</li>
          <li>create / revoke project API keys</li>
          <li>per-project usage view</li>
        </ul>
      </div>
    </>
  );
}
