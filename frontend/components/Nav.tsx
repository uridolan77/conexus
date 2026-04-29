import Link from "next/link";

const links = [
  { href: "/", label: "Dashboard" },
  { href: "/providers", label: "Providers" },
  { href: "/projects", label: "Projects" },
  { href: "/requests", label: "Requests" },
  { href: "/smoke-tests", label: "Smoke Tests" },
];

export function Nav() {
  return (
    <nav className="nav">
      <h1>Conexus</h1>
      <ul>
        {links.map((l) => (
          <li key={l.href}>
            <Link href={l.href}>{l.label}</Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
