"use client";

import AuthGuard from "@/components/AuthGuard";
import ErrorBoundary from "@/components/ErrorBoundary";

/** Dedicated docs chrome — not AppShell. */
export default function DocsLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <ErrorBoundary title="Guide couldn’t load">{children}</ErrorBoundary>
    </AuthGuard>
  );
}
