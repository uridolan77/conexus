import type { ReactNode } from "react";
import { getEnvironmentLabel } from "@/lib/api";
import { Sidebar } from "./Sidebar";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="shell">
      <Sidebar environment={getEnvironmentLabel()} />
      <main className="main">{children}</main>
    </div>
  );
}
