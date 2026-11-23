"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function RedirectMailbox() {
  const router = useRouter();
  const params = useSearchParams();
  useEffect(() => {
    const query = params.toString();
    router.replace(query ? `/settings/mailbox?${query}` : "/settings/mailbox");
  }, [params, router]);
  return null;
}

export default function Page() {
  return (
    <Suspense fallback={null}>
      <RedirectMailbox />
    </Suspense>
  );
}
