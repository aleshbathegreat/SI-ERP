"use client";

import { Suspense, useMemo } from "react";
import { useSearchParams } from "next/navigation";
import EntityFormRoute from "@/components/crud/EntityFormRoute";
import { getEntityDef } from "@/lib/entityCrudDefs";

const def = getEntityDef("crm/activities")!;

function NewActivityForm() {
  const params = useSearchParams();
  const empty = useMemo(
    () => ({
      ...def.empty,
      lead: params.get("lead") || "",
      opportunity: params.get("opportunity") || "",
      due_date: params.get("due") || "",
      starts_at: params.get("start") || "",
      ends_at: params.get("end") || "",
    }),
    [params]
  );

  return (
    <EntityFormRoute
      moduleKey={def.moduleKey}
      resourcePath={def.apiPath}
      entityLabel={def.entityLabel}
      basePath={"/" + def.route}
      mode="create"
      fields={def.fields}
      empty={empty}
    />
  );
}

export default function Page() {
  return (
    <Suspense fallback={null}>
      <NewActivityForm />
    </Suspense>
  );
}
