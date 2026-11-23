"use client";

import EntityFormRoute from "@/components/crud/EntityFormRoute";
import { getEntityDef } from "@/lib/entityCrudDefs";

const def = getEntityDef("dms/folders")!;

export default function Page() {
  return (
    <EntityFormRoute
      moduleKey={def.moduleKey}
      resourcePath={def.apiPath}
      entityLabel={def.entityLabel}
      basePath={`/${def.route}`}
      mode="create"
      fields={def.fields}
      empty={def.empty}
      titles={{ create: "New folder" }}
    />
  );
}
