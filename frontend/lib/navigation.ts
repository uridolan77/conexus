export type NavStatus = "available" | "planned";

export type NavItem = {
  href: string;
  label: string;
  description: string;
  status?: NavStatus;
};

export type NavSection = {
  title: string;
  items: NavItem[];
};

export const NAV_SECTIONS: NavSection[] = [
  {
    title: "Overview",
    items: [
      { href: "/", label: "Dashboard", description: "Operational home" },
    ],
  },
  {
    title: "Operations",
    items: [
      { href: "/projects", label: "Projects", description: "Gateway clients and keys" },
      { href: "/providers", label: "Providers", description: "Upstream credentials" },
      { href: "/playground", label: "Playground", description: "Manual chat completion test" },
      { href: "/requests", label: "Requests", description: "Gateway activity" },
      { href: "/usage", label: "Usage", description: "Costs and rollups" },
      { href: "/activity", label: "Activity", description: "Admin audit log" },
      { href: "/limits", label: "Limits", description: "Limit modes and tooling" },
    ],
  },
  {
    title: "Routing",
    items: [
      { href: "/routing", label: "Routing", description: "Policy and aliases" },
      { href: "/smoke-tests", label: "Smoke Tests", description: "End-to-end checks" },
      { href: "/adapter-profiles", label: "Adapter Profiles", description: "Gateway registry state" },
    ],
  },
  {
    title: "System",
    items: [
      { href: "/health", label: "Health", description: "Health and readiness checks" },
      { href: "/settings", label: "Settings", description: "Read-only config summary" },
    ],
  },
  {
    title: "Adaptation",
    items: [
      { href: "/adaptation/plans", label: "Adaptation Plans", description: "Review and approve plans" },
      { href: "/adaptation/runs", label: "Adaptation Runs", description: "Inspect run progress and artifacts" },
      { href: "/adaptation/queue", label: "Adaptation Queue", description: "Diagnostics and repair tools" },
      { href: "/adaptation/profiles", label: "Adaptation Profiles", description: "Review produced adapter profiles" },
    ],
  },
];
