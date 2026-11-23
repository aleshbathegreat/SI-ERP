"use client";

import EntityFormRoute from "@/components/crud/EntityFormRoute";
import { getEntityDef } from "@/lib/entityCrudDefs";
import { useParams } from "next/navigation";

const def = getEntityDef("finance/currencies")!;

export default function Page() {
  const params = useParams();
  const id = String(params.id);
  return (
    <EntityFormRoute
      moduleKey={def.moduleKey}
      resourcePath={def.apiPath}
      entityLabel={def.entityLabel}
      basePath={`/${def.route}`}
      mode="edit"
      id={id}
      fields={def.fields}
      empty={def.empty}
      subtitle={def.formSubtitle}
    />
  );
}
