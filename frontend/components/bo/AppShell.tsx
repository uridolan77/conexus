"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { getEnvironmentLabel } from "@/lib/api";
import { Sidebar } from "./Sidebar";

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  if (pathname === "/login") {
    return <main className="auth-standalone">{children}</main>;
  }

  return (
    <div className="shell">
      <Sidebar environment={getEnvironmentLabel()} />
      <main className="main">{children}</main>
    </div>
  );
}
