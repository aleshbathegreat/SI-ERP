"use client";

import AuthGuard from "@/components/AuthGuard";
import ErrorBoundary from "@/components/ErrorBoundary";
import ModuleGate from "@/components/ModuleGate";
import EssShell from "@/components/ess/EssShell";

export default function EmployeeLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <ModuleGate module="ess">
        <>
          {/* Fraunces for ESS display headings */}
          {/* eslint-disable-next-line @next/next/no-page-custom-font */}
          <link
            href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&display=swap"
            rel="stylesheet"
          />
          <EssShell>
            <ErrorBoundary title="Employee portal couldn’t load">{children}</ErrorBoundary>
          </EssShell>
        </>
      </ModuleGate>
    </AuthGuard>
  );
}
