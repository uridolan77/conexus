"use client";

import Link from "next/link";
import type {
  ButtonHTMLAttributes,
  ComponentPropsWithoutRef,
  ReactNode,
} from "react";
import { useEffect, useId, useState } from "react";

type Tone = "neutral" | "success" | "warning" | "danger" | "info";

export function PageHeader({
  title,
  eyebrow,
  description,
  actions,
}: {
  title: string;
  eyebrow?: string;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h2>{title}</h2>
        {description && <p className="page-description">{description}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  );
}

export function SectionHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="section-header">
      <div>
        <h3>{title}</h3>
        {description && <p className="muted">{description}</p>}
      </div>
      {actions && <div className="inline-actions">{actions}</div>}
    </div>
  );
}

export function Card({
  children,
  className,
  ...props
}: {
  children: ReactNode;
  className?: string;
} & Omit<ComponentPropsWithoutRef<"section">, "className" | "children">) {
  return (
    <section
      className={["card", className].filter(Boolean).join(" ")}
      {...props}
    >
      {children}
    </section>
  );
}

export function Button({
  children,
  variant = "primary",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger" | "ghost";
}) {
  return (
    <button
      className={["button", `button-${variant}`, className].filter(Boolean).join(" ")}
      {...props}
    >
      {children}
    </button>
  );
}

export function LinkButton({
  href,
  children,
  variant = "secondary",
}: {
  href: string;
  children: ReactNode;
  variant?: "primary" | "secondary" | "ghost";
}) {
  return (
    <Link className={`button button-${variant}`} href={href}>
      {children}
    </Link>
  );
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: ReactNode;
  children: ReactNode;
}) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  );
}

export function Input(props: ComponentPropsWithoutRef<"input">) {
  return <input className="input" {...props} />;
}

export function Select(props: ComponentPropsWithoutRef<"select">) {
  return <select className="input" {...props} />;
}

export function Textarea(props: ComponentPropsWithoutRef<"textarea">) {
  return <textarea className="input textarea" {...props} />;
}

export function FormRow({ children }: { children: ReactNode }) {
  return <div className="form-row">{children}</div>;
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: Tone;
}) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

export function StatusBadge({
  status,
}: {
  status:
    | "active"
    | "revoked"
    | "ok"
    | "passed"
    | "failed"
    | "never"
    | "running"
    | "not-run";
}) {
  const tone: Tone =
    status === "active" || status === "ok" || status === "passed"
      ? "success"
      : status === "failed" || status === "revoked"
        ? "danger"
        : status === "running"
          ? "info"
          : "neutral";
  const label = status === "not-run" ? "not run" : status;
  return <Badge tone={tone}>{label}</Badge>;
}

export function Alert({
  children,
  tone = "info",
  title,
}: {
  children: ReactNode;
  tone?: Tone;
  title?: string;
}) {
  return (
    <div className={`alert alert-${tone}`} role={tone === "danger" ? "alert" : "status"}>
      {title && <strong>{title}</strong>}
      <div>{children}</div>
    </div>
  );
}

export function EmptyState({
  title,
  children,
  action,
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <h4>{title}</h4>
      <p>{children}</p>
      {action && <div className="empty-action">{action}</div>}
    </div>
  );
}

export function LoadingState({ label = "Loading..." }: { label?: string }) {
  return <p className="state-text">{label}</p>;
}

export function ErrorState({ message }: { message: ReactNode }) {
  return <Alert tone="danger">{message}</Alert>;
}

export function Table({
  children,
  "aria-label": ariaLabel,
}: {
  children: ReactNode;
  "aria-label": string;
}) {
  return (
    <div className="table-wrap">
      <table className="table" aria-label={ariaLabel}>
        {children}
      </table>
    </div>
  );
}

export function SecretValue({ value }: { value: string }) {
  return <code className="secret-value">{value}</code>;
}

export function KeyValueGrid({
  items,
}: {
  items: Array<{ label: string; value: ReactNode }>;
}) {
  return (
    <dl className="kv">
      {items.map((item) => (
        <div key={item.label} className="kv-row">
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
}) {
  return (
    <div className="stat-card">
      <span>{label}</span>
      <strong>{value}</strong>
      {hint && <small>{hint}</small>}
    </div>
  );
}

export function Stepper({
  steps,
}: {
  steps: Array<{ label: string; status: "not-run" | "running" | "passed" | "failed"; detail?: ReactNode }>;
}) {
  return (
    <ol className="stepper">
      {steps.map((step) => (
        <li key={step.label} className={`step step-${step.status}`}>
          <div>
            <span>{step.label}</span>
            {step.detail && <small>{step.detail}</small>}
          </div>
          <StatusBadge status={step.status} />
        </li>
      ))}
    </ol>
  );
}

export function ConfirmAction({
  children,
  message,
  onConfirm,
  disabled,
  variant = "danger",
}: {
  children: ReactNode;
  message: string;
  onConfirm: () => void;
  disabled?: boolean;
  variant?: "danger" | "secondary";
}) {
  return (
    <Button
      type="button"
      variant={variant}
      disabled={disabled}
      onClick={() => {
        if (window.confirm(message)) onConfirm();
      }}
    >
      {children}
    </Button>
  );
}

export function JsonBlock({
  value,
  title = "Raw JSON",
  defaultOpen = false,
}: {
  value: unknown;
  title?: string;
  defaultOpen?: boolean;
}) {
  return (
    <details className="details-block" open={defaultOpen}>
      <summary>{title}</summary>
      <pre>{JSON.stringify(value, null, 2)}</pre>
    </details>
  );
}

// ---------------------------------------------------------------------------
// New primitives
// ---------------------------------------------------------------------------

export function CopyButton({
  value,
  label = "Copy",
  onCopied,
  onError,
}: {
  value: string;
  label?: string;
  onCopied?: () => void;
  onError?: (err: unknown) => void;
}) {
  const [status, setStatus] = useState<"idle" | "copied" | "failed">("idle");
  async function copy() {
    let ok = false;
    try {
      await navigator.clipboard.writeText(value);
      ok = true;
    } catch {
      // Fallback for non-secure contexts (tests, older browsers)
      try {
        const el = document.createElement("textarea");
        el.value = value;
        el.style.position = "fixed";
        el.style.opacity = "0";
        document.body.appendChild(el);
        el.select();
        ok = document.execCommand("copy");
        document.body.removeChild(el);
      } catch (fallbackErr) {
        onError?.(fallbackErr);
        setStatus("failed");
        window.setTimeout(() => setStatus("idle"), 1500);
        return;
      }
    }
    if (ok) {
      onCopied?.();
      setStatus("copied");
    } else {
      setStatus("failed");
    }
    window.setTimeout(() => setStatus("idle"), 1500);
  }
  return (
    <Button type="button" variant="secondary" onClick={copy}>
      {status === "copied" ? "Copied" : status === "failed" ? "Copy failed" : label}
    </Button>
  );
}

export function PageState({
  loading,
  loadingLabel,
  error,
  empty,
  emptyTitle,
  emptyBody,
  action,
  children,
}: {
  loading?: boolean;
  loadingLabel?: string;
  error?: string | null;
  empty?: boolean;
  emptyTitle?: string;
  emptyBody?: ReactNode;
  /** Optional action rendered inside the empty state. */
  action?: ReactNode;
  children: ReactNode;
}) {
  if (loading) return <LoadingState label={loadingLabel} />;
  if (error) return <ErrorState message={error} />;
  if (empty) {
    return (
      <EmptyState title={emptyTitle ?? "No data"} action={action}>
        {emptyBody ?? "Nothing to show yet."}
      </EmptyState>
    );
  }
  return <>{children}</>;
}

export function Toolbar({ children }: { children: ReactNode }) {
  return <div className="toolbar">{children}</div>;
}

export function FilterBar({ children }: { children: ReactNode }) {
  return <div className="filter-bar">{children}</div>;
}

export function InlineCode({ children }: { children: ReactNode }) {
  return <code className="inline-code">{children}</code>;
}

export function CopyableCode({ value }: { value: string }) {
  return (
    <span className="copyable-code">
      <InlineCode>{value}</InlineCode>
      <CopyButton value={value} label="Copy" />
    </span>
  );
}

export function RefreshButton({
  onClick,
  loading,
}: {
  onClick: () => void;
  loading?: boolean;
}) {
  return (
    <Button type="button" variant="secondary" onClick={onClick} disabled={loading}>
      {loading ? "Refreshing…" : "↻ Refresh"}
    </Button>
  );
}

export function ConfirmButton({
  children,
  message,
  onConfirm,
  disabled,
  variant = "danger",
}: {
  children: ReactNode;
  message: string;
  onConfirm: () => void;
  disabled?: boolean;
  variant?: "danger" | "secondary";
}) {
  return (
    <ConfirmAction
      message={message}
      onConfirm={onConfirm}
      disabled={disabled}
      variant={variant}
    >
      {children}
    </ConfirmAction>
  );
}

export function MetricCard({
  label,
  value,
  hint,
  delta,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  delta?: { value: string; positive: boolean };
}) {
  return (
    <div className="stat-card">
      <span>{label}</span>
      <strong>{value}</strong>
      {delta && (
        <small className={delta.positive ? "metric-delta-up" : "metric-delta-down"}>
          {delta.value}
        </small>
      )}
      {hint && <small>{hint}</small>}
    </div>
  );
}

type DataTableColumn<T> = {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
};

export function DataTable<T extends { id?: string }>({
  columns,
  rows,
  "aria-label": ariaLabel,
  getRowKey,
  emptyMessage,
}: {
  columns: DataTableColumn<T>[];
  rows: T[];
  "aria-label": string;
  getRowKey?: (row: T, index: number) => string;
  /** Rendered as a full-width cell when rows is empty. */
  emptyMessage?: ReactNode;
}) {
  return (
    <Table aria-label={ariaLabel}>
      <thead>
        <tr>
          {columns.map((col) => (
            <th key={col.key}>{col.header}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.length === 0 && emptyMessage ? (
          <tr>
            <td colSpan={columns.length} className="state-text">
              {emptyMessage}
            </td>
          </tr>
        ) : (
          rows.map((row, i) => (
            <tr key={getRowKey ? getRowKey(row, i) : (row.id ?? i)}>
              {columns.map((col) => (
                <td key={col.key}>{col.render(row)}</td>
              ))}
            </tr>
          ))
        )}
      </tbody>
    </Table>
  );
}

export function DetailDrawer({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  // Note: no focus trap yet. Keyboard navigation stays in page until that is added.
}) {
  const titleId = useId();

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="drawer">
      <div className="drawer-backdrop" onClick={onClose} aria-hidden="true" />
      <div
        className="drawer-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <div className="drawer-header">
          <h3 id={titleId}>{title}</h3>
          <Button
            type="button"
            variant="ghost"
            onClick={onClose}
            aria-label="Close"
          >
            ✕
          </Button>
        </div>
        <div className="drawer-body">{children}</div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tiny utility primitives
// ---------------------------------------------------------------------------

/** Inline field validation error. */
export function FieldError({ children }: { children: ReactNode }) {
  return (
    <span className="field-error" role="alert">
      {children}
    </span>
  );
}

/** Muted helper text beneath a field or section. */
export function HelpText({ children }: { children: ReactNode }) {
  return <p className="help-text">{children}</p>;
}

/** Monospace chip for short codes, IDs, or model names. */
export function CodeChip({ children }: { children: ReactNode }) {
  return <code className="code-chip">{children}</code>;
}

/** Alias for Badge — use for status-style pills to make intent clear at callsite. */
export function StatusPill({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: Tone;
}) {
  return <Badge tone={tone}>{children}</Badge>;
}

/** Vertical gap between sections inside a page. */
export function SectionGap() {
  return <div className="section-gap" aria-hidden="true" />;
}
