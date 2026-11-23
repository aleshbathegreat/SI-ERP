"use client";

import { useParams } from "next/navigation";
import EntityFormRoute from "@/components/crud/EntityFormRoute";
import { getEntityDef } from "@/lib/entityCrudDefs";

const def = getEntityDef("dms/metadata-types")!;

export default function Page() {
  const params = useParams();
  return (
    <EntityFormRoute
      moduleKey={def.moduleKey}
      resourcePath={def.apiPath}
      entityLabel={def.entityLabel}
      basePath={`/${def.route}`}
      mode="edit"
      id={String(params.id)}
      fields={def.fields}
      empty={def.empty}
      titles={{ edit: "Edit metadata type" }}
    />
  );
}