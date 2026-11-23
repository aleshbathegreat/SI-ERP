"use client";

import AppShell from "@/components/AppShell";
import AuthGuard from "@/components/AuthGuard";
import ErrorBoundary from "@/components/ErrorBoundary";

export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <AppShell>
        <ErrorBoundary title="This module couldn’t load">{children}</ErrorBoundary>
      </AppShell>
    </AuthGuard>
  );
}
