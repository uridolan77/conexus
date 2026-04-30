"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  {
    href: "/",
    label: "Dashboard",
    description: "Operational home",
  },
  {
    href: "/audit",
    label: "Audit",
    description: "Sensitive admin actions",
  },
  {
    href: "/projects",
    label: "Projects",
    description: "Gateway clients and keys",
  },
  {
    href: "/providers",
    label: "Providers",
    description: "Upstream credentials",
  },
  {
    href: "/requests",
    label: "Requests",
    description: "Gateway activity",
  },
  {
    href: "/usage",
    label: "Usage",
    description: "Costs and rollups",
  },
  {
    href: "/routing",
    label: "Routing",
    description: "Policy and aliases",
  },
  {
    href: "/smoke-tests",
    label: "Smoke Tests",
    description: "End-to-end checks",
  },
  {
    href: "/adaptation/plans",
    label: "Adaptation Plans",
    description: "Review and approve plans",
  },
  {
    href: "/adaptation/runs",
    label: "Adaptation Runs",
    description: "Inspect run progress and artifacts",
  },
  {
    href: "/adaptation/queue",
    label: "Adaptation Queue",
    description: "Diagnostics and repair tools",
  },
  {
    href: "/adaptation/profiles",
    label: "Adaptation Profiles",
    description: "Review produced adapter profiles",
  },
];

export function Sidebar({ environment }: { environment: string }) {
  const pathname = usePathname();
  return (
    <aside className="sidebar">
      <div className="brand">
        <div>
          <h1>Conexus</h1>
          <p>LLM gateway BO</p>
        </div>
        <span className="environment-pill">{environment}</span>
      </div>
      <nav aria-label="Back office navigation">
        <ul className="nav-list">
          {links.map((link) => {
            const active =
              link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
            return (
              <li key={link.href}>
                <Link
                  href={link.href}
                  className={active ? "nav-link nav-link-active" : "nav-link"}
                  aria-current={active ? "page" : undefined}
                >
                  <span>{link.label}</span>
                  <small>{link.description}</small>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
}
