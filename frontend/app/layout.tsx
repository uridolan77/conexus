import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Nav } from "../components/Nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "Conexus",
  description: "LLM gateway and back-office",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <Nav />
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}
