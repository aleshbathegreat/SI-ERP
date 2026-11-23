"use client";

import { useAppSelector } from "@/store/hooks";

export function usePlatformCaps() {
  const isPlatformUser = useAppSelector((s) => s.auth.isPlatformUser);
  const platformRole = useAppSelector((s) => s.auth.platformRole);
  const caps = useAppSelector((s) => s.auth.platformCapabilities);
  const user = useAppSelector((s) => s.auth.user);

  const effectiveCaps =
    caps.length > 0
      ? caps
      : user?.is_superuser
        ? [
            "overview",
            "packages",
            "tenants",
            "tenants.extend",
            "invoices",
            "invoices.mark_paid",
            "smtp",
            "payfast",
            "domains",
            "tickets",
            "tickets.assign",
            "staff",
          ]
        : [];

  const can = (cap: string) =>
    !!user?.is_superuser || effectiveCaps.includes(cap);

  return {
    isPlatformUser: isPlatformUser || !!user?.is_superuser,
    platformRole: platformRole || (user?.is_superuser ? "owner" : null),
    caps: effectiveCaps,
    can,
  };
}
