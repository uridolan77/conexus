import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AppShell } from "@/components/bo/AppShell";
import "./globals.css";

export const metadata: Metadata = {
  title: "Conexus",
  description: "LLM gateway and back-office",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
