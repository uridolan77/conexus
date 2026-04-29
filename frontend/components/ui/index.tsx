"use client";

import Link from "next/link";
import type {
  ButtonHTMLAttributes,
  ComponentPropsWithoutRef,
  ReactNode,
} from "react";
import { useState } from "react";

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
}: {
  children: ReactNode;
  className?: string;
}) {
  return <section className={["card", className].filter(Boolean).join(" ")}>{children}</section>;
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

export function CopyButton({
  value,
  label = "Copy",
}: {
  value: string;
  label?: string;
}) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    await navigator.clipboard.writeText(value);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }
  return (
    <Button type="button" variant="secondary" onClick={copy}>
      {copied ? "Copied" : label}
    </Button>
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
