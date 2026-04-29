import {
  Card,
  EmptyState,
  LinkButton,
  PageHeader,
  SectionHeader,
  Table,
} from "@/components/ui";

export default function RequestsPage() {
  const futureColumns = [
    "request_id",
    "project",
    "provider",
    "model",
    "status",
    "latency",
    "tokens",
    "cost",
    "fallback",
    "timestamp",
  ];

  return (
    <>
      <PageHeader
        eyebrow="Gateway activity"
        title="Requests"
        description="Gateway request logs will appear here once the BO has a request-list API. Until then, this page stays honest about what is available and points you to the smoke test path that creates real logs."
        actions={<LinkButton href="/smoke-tests" variant="primary">Run Smoke Test</LinkButton>}
      />

      <Card>
        <SectionHeader
          title="Request Monitoring"
          description="The backend currently persists gateway request logs for counting and future monitoring, but it does not expose a list endpoint yet."
        />
        <EmptyState
          title="No request list API is available yet"
          action={<LinkButton href="/smoke-tests">Run a gateway smoke test</LinkButton>}
        >
          When a request-list endpoint is added, this page will show real gateway traffic, not mocked operational data.
        </EmptyState>
      </Card>

      <Card>
        <SectionHeader
          title="Planned Table Shape"
          description="These are the fields this page is structured to display once the backend exposes request rows."
        />
        <Table aria-label="Future request columns">
          <thead>
            <tr>
              {futureColumns.map((column) => (
                <th key={column}>{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              {futureColumns.map((column) => (
                <td key={column} className="muted">
                  pending API
                </td>
              ))}
            </tr>
          </tbody>
        </Table>
      </Card>
    </>
  );
}
