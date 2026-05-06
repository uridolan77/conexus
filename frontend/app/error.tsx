"use client";

import { useEffect } from "react";

import { Button, Card, PageHeader, SectionHeader } from "@/components/ui";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Best-effort console signal for debugging production render failures.
    // eslint-disable-next-line no-console
    console.error("frontend_global_error", error);
  }, [error]);

  return (
    <div className="stack">
      <PageHeader
        eyebrow="Frontend"
        title="Something went wrong"
        description="The app hit an unexpected render error. You can retry safely."
      />

      <Card>
        <SectionHeader title="Recovery" description="Try again or go back to the dashboard." />
        <div className="inline-actions">
          <Button type="button" onClick={reset}>
            Retry
          </Button>
          <Button type="button" variant="secondary" onClick={() => (window.location.href = "/")}>
            Go to dashboard
          </Button>
        </div>

        <details className="stack" style={{ marginTop: 12 }}>
          <summary className="muted">Technical details</summary>
          <pre className="codeblock wrap-anywhere">{String(error?.message || error)}</pre>
          {error?.digest ? <p className="muted">digest: {error.digest}</p> : null}
        </details>
      </Card>
    </div>
  );
}

