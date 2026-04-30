"use client";

import { useState } from "react";
import { Badge, Card, EmptyState, KeyValueGrid, SectionHeader, Table } from "@/components/ui";
import type { EvaluationEvidence, EvalQuestionEvidence } from "@/lib/adaptationTypes";
import { formatDate } from "@/lib/api";

function bool(v: unknown) {
  return v === true || v === "true";
}

function QuestionCard({ q, idx }: { q: EvalQuestionEvidence; idx: number }) {
  const [open, setOpen] = useState(false);
  const citation = q.citationValidation;
  const issues = citation?.issues ?? [];
  const blockingIssues = issues.filter((i) => bool(i.blocking));
  const nonBlockingIssues = issues.filter((i) => !bool(i.blocking));
  const passed = citation?.passed;
  const score = citation?.lexicalSupportScore;

  return (
    <div
      className="stack"
      style={{
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius-sm)",
        padding: "var(--space-3)",
      }}
    >
      <button
        type="button"
        className="inline-actions"
        style={{ justifyContent: "space-between", width: "100%", background: "none", border: "none", cursor: "pointer", padding: 0 }}
        onClick={() => setOpen(!open)}
      >
        <span>
          <code className="wrap-anywhere">{q.questionId || `question-${idx}`}</code>
          {q.category ? (
            <span className="muted"> · {q.category}</span>
          ) : null}
        </span>
        <span className="muted">{open ? "▼" : "▶"}</span>
      </button>
      {open && (
        <div className="stack">
          <p>{q.question || "—"}</p>
          <KeyValueGrid
            items={[
              { label: "answered", value: q.answered ? <Badge tone="success">yes</Badge> : <Badge tone="neutral">no</Badge> },
              { label: "latencyMs", value: String(q.latencyMs ?? "—") },
              { label: "estimatedCost", value: String(q.estimatedCost ?? "—") },
              {
                label: "citation",
                value:
                  passed === true ? (
                    <Badge tone="success">passed</Badge>
                  ) : passed === false ? (
                    <Badge tone="danger">failed</Badge>
                  ) : (
                    "—"
                  ),
              },
              {
                label: "lexicalSupportScore",
                value: score !== undefined && score !== null ? String(score) : "—",
              },
            ]}
          />
          {q.answerExcerpt ? (
            <div>
              <p className="muted">Answer excerpt</p>
              <pre style={{ whiteSpace: "pre-wrap", fontSize: "var(--font-sm)" }}>{q.answerExcerpt}</pre>
            </div>
          ) : null}
          {blockingIssues.length > 0 && (
            <div>
              <p style={{ color: "var(--color-danger)", fontSize: "var(--font-sm)" }}>Blocking citation issues</p>
              <ul style={{ fontSize: "var(--font-sm)" }}>
                {blockingIssues.map((i, j) => (
                  <li key={j}>
                    {i.code ? <code>{i.code}</code> : null} {i.message ?? ""}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {nonBlockingIssues.length > 0 && (
            <div>
              <p style={{ color: "var(--color-warning)", fontSize: "var(--font-sm)" }}>Non-blocking issues</p>
              <ul style={{ fontSize: "var(--font-sm)" }}>
                {nonBlockingIssues.map((i, j) => (
                  <li key={j}>
                    {i.code ? <code>{i.code}</code> : null} {i.message ?? ""}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div className="muted" style={{ fontSize: "var(--font-sm)" }}>
            <span>Sources: </span>
            <code>{q.requiredSourceIds?.join(", ") || "—"}</code>
            {" · "}
            <span>Documents: </span>
            <code>{q.requiredDocumentIds?.join(", ") || "—"}</code>
            {" · "}
            <span>Chunks: </span>
            <code>{q.requiredChunkIds?.join(", ") || "—"}</code>
          </div>
          {q.retrievedContexts?.length ? (
            <div>
              <p className="muted small">Retrieved context excerpts</p>
              <ul className="stack">
                {q.retrievedContexts.map((c, j) => (
                  <li
                    key={j}
                    className="stack"
                    style={{
                      border: "1px solid var(--color-border)",
                      borderRadius: "var(--radius-sm)",
                      padding: "var(--space-2)",
                      fontSize: "var(--font-sm)",
                    }}
                  >
                    <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{c.excerpt ?? "—"}</pre>
                    <div className="muted">
                      {c.sourceId ? <span>source: {c.sourceId} </span> : null}
                      {c.documentId ? <span>doc: {c.documentId} </span> : null}
                      {c.chunkId ? <span>chunk: {c.chunkId}</span> : null}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}

export function EvaluationEvidencePanel({
  evidence,
  status,
}: {
  evidence: EvaluationEvidence | null;
  status: "loading" | "ok" | "404" | "error";
}) {
  if (status === "loading") {
    return (
      <Card>
        <SectionHeader title="Evaluation evidence" />
        <p className="muted">Loading evaluation projection…</p>
      </Card>
    );
  }
  if (status === "404") {
    return (
      <Card>
        <SectionHeader title="Evaluation evidence" />
        <EmptyState title="No evaluation evidence">
          No evaluation evidence projection is available for this run.
        </EmptyState>
      </Card>
    );
  }
  if (status === "error") {
    return (
      <Card>
        <SectionHeader title="Evaluation evidence" />
        <EmptyState title="Could not load evidence">The evaluation endpoint returned an error.</EmptyState>
      </Card>
    );
  }
  if (!evidence || !evidence.id) {
    return (
      <Card>
        <SectionHeader title="Evaluation evidence" />
        <EmptyState title="No data">No evaluation payload was returned.</EmptyState>
      </Card>
    );
  }

  const sec = evidence.securitySummary ?? {};
  const metrics = evidence.metrics ?? [];
  const gates = evidence.gates ?? [];
  const questions = evidence.questions ?? [];

  return (
    <Card id="evaluation-evidence">
      <SectionHeader
        title="Evaluation evidence"
        description="Persisted evaluation projection (truncated excerpts only)."
      />

      <h4 style={{ marginTop: "var(--space-5)", marginBottom: "var(--space-2)" }}>Evaluation Summary</h4>
      <KeyValueGrid
        items={[
          { label: "evidence id", value: <code className="wrap-anywhere">{evidence.id}</code> },
          { label: "runId", value: <code className="wrap-anywhere">{evidence.runId}</code> },
          { label: "planId", value: <code className="wrap-anywhere">{evidence.planId}</code> },
          { label: "domainKey", value: <code className="wrap-anywhere">{evidence.domainKey}</code> },
          { label: "evalSetId", value: <code className="wrap-anywhere">{evidence.evalSetId}</code> },
          { label: "createdAt", value: formatDate(evidence.createdAt) },
          { label: "compositeScore", value: String(evidence.compositeScore) },
          { label: "projectionVersion", value: evidence.projectionVersion || "—" },
          { label: "evidenceHash", value: <code className="wrap-anywhere">{evidence.evidenceHash || "—"}</code> },
        ]}
      />

      <h4 style={{ marginTop: "var(--space-5)", marginBottom: "var(--space-2)" }}>Security Summary</h4>
      {sec.summary || sec.riskLevel || sec.notes ? (
        <KeyValueGrid
          items={[
            { label: "summary", value: sec.summary ?? "—" },
            { label: "riskLevel", value: sec.riskLevel ?? "—" },
            { label: "notes", value: sec.notes ?? "—" },
          ]}
        />
      ) : (
        <p className="muted">No security summary fields.</p>
      )}

      <h4 style={{ marginTop: "var(--space-5)", marginBottom: "var(--space-2)" }}>Metrics</h4>
      {metrics.length === 0 ? (
        <p className="muted">No metrics.</p>
      ) : (
        <Table aria-label="Evaluation metrics">
          <thead>
            <tr>
              <th>Key</th>
              <th>Value</th>
              <th>Threshold</th>
              <th>Passed</th>
            </tr>
          </thead>
          <tbody>
            {metrics.map((m, idx) => {
              const key = m.key ?? m.metricKey ?? "—";
              const passed = m.passed;
              return (
                <tr key={`${key}-${idx}`}>
                  <td>
                    <code className="wrap-anywhere">{key}</code>
                  </td>
                  <td>
                    <code>{String(m.value ?? "—")}</code>
                  </td>
                  <td>
                    <code>{String(m.threshold ?? "—")}</code>
                  </td>
                  <td>
                    {passed === true ? (
                      <Badge tone="success">passed</Badge>
                    ) : passed === false ? (
                      <Badge tone="danger">failed</Badge>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      )}

      <h4 style={{ marginTop: "var(--space-5)", marginBottom: "var(--space-2)" }}>Gate Results</h4>
      {gates.length === 0 ? (
        <p className="muted">No gates.</p>
      ) : (
        <Table aria-label="Evaluation gates">
          <thead>
            <tr>
              <th>Gate</th>
              <th>Blocking</th>
              <th>Passed</th>
              <th>Message</th>
            </tr>
          </thead>
          <tbody>
            {gates.map((g, idx) => {
              const key = g.key ?? g.gateKey ?? "—";
              const blocking = bool(g.blocking);
              const passed = g.passed;
              return (
                <tr key={`${key}-${idx}`}>
                  <td>
                    <code className="wrap-anywhere">{key}</code>
                  </td>
                  <td>{blocking ? <Badge tone="warning">blocking</Badge> : "—"}</td>
                  <td>
                    {passed === true ? (
                      <Badge tone="success">passed</Badge>
                    ) : passed === false ? (
                      <Badge tone={blocking ? "danger" : "warning"}>failed</Badge>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="truncate">{g.message ?? "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      )}

      <h4 style={{ marginTop: "var(--space-5)", marginBottom: "var(--space-2)" }}>Question Evidence</h4>
      {questions.length === 0 ? (
        <p className="muted">No question rows.</p>
      ) : (
        <div className="stack">
          {questions.map((q, idx) => (
            <QuestionCard key={`${q.questionId}-${idx}`} q={q} idx={idx} />
          ))}
        </div>
      )}
    </Card>
  );
}
