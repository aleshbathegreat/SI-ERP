"use client";

import { useCallback, useMemo } from "react";
import { useAppSelector } from "@/store/hooks";

export function usePermissions() {
  const permissions = useAppSelector((s) => s.auth.permissions);
  const isOwner = useAppSelector((s) => s.auth.user?.is_owner === true);

  const can = useCallback(
    (module: string, action: string = "view") => {
      // Package-filtered map from /auth/me (owners included). Sidebar + ModuleGate
      // must match the same entitled modules.
      const actions = permissions?.[module];
      return Array.isArray(actions) && actions.includes(action);
    },
    [permissions]
  );

  const canAny = useCallback(
    (module: string, actions: string[]) => actions.some((a) => can(module, a)),
    [can]
  );

  return useMemo(
    () => ({
      permissions,
      isOwner,
      can,
      canAny,
      canView: (module: string) => can(module, "view"),
      canAdd: (module: string) => can(module, "add"),
      canChange: (module: string) => can(module, "change"),
      canDelete: (module: string) => can(module, "delete"),
    }),
    [permissions, isOwner, can, canAny]
  );
}
