"use client";

import { useMemo } from "react";
import { useSelector } from "react-redux";
import EntityFormRoute from "@/components/crud/EntityFormRoute";
import { getEntityDef } from "@/lib/entityCrudDefs";
import { normalizeCurrency } from "@/lib/currencies";
import type { RootState } from "@/store";

const def = getEntityDef("payroll/structures")!;

export default function Page() {
  const orgCurrency = useSelector(
    (s: RootState) => s.auth.organization?.currency
  );
  const empty = useMemo(
    () => ({
      ...def.empty,
      currency: normalizeCurrency(orgCurrency, String(def.empty.currency || "PKR")),
    }),
    [orgCurrency]
  );

  return (
    <EntityFormRoute
      moduleKey={def.moduleKey}
      resourcePath={def.apiPath}
      entityLabel={def.entityLabel}
      basePath={`/${def.route}`}
      mode="create"
      fields={def.fields}
      empty={empty}
    />
  );
}
