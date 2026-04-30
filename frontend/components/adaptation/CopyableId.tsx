"use client";

import { CopyButton } from "@/components/ui";

export function CopyableId({ value, label }: { value: string; label?: string }) {
  if (!value) return <span>—</span>;
  return (
    <span className="inline-actions">
      <code className="wrap-anywhere">{value}</code>
      <CopyButton value={value} label={label ?? "Copy"} />
    </span>
  );
}
