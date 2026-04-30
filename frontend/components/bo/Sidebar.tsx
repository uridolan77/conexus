"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_SECTIONS } from "@/lib/navigation";

function isActive(href: string, pathname: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

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
        {NAV_SECTIONS.map((section) => (
          <div key={section.title} className="nav-section">
            <p className="nav-group-label">{section.title}</p>
            <ul className="nav-list">
              {section.items.map((item) => {
                const active = isActive(item.href, pathname);
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className={active ? "nav-link nav-link-active" : "nav-link"}
                      aria-current={active ? "page" : undefined}
                    >
                      <span>{item.label}</span>
                      <small>{item.description}</small>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>
    </aside>
  );
}
