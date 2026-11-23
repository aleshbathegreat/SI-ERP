"use client";

import EntityFormRoute from "@/components/crud/EntityFormRoute";
import LeadDuplicateHint from "@/components/crm/LeadDuplicateHint";
import { getEntityDef } from "@/lib/entityCrudDefs";
import { useParams } from "next/navigation";


const def = getEntityDef("crm/leads")!;

export default function Page() {
  const params = useParams();
  const id = String(params.id);

  return (
    <EntityFormRoute
      moduleKey={def.moduleKey}
      resourcePath={def.apiPath}
      entityLabel={def.entityLabel}
      basePath={"/" + def.route}
      mode="edit"
      id={id}
      fields={def.fields}
      empty={def.empty}
      belowFields={({ form }) => (
        <LeadDuplicateHint
          email={form.email}
          phone={form.phone}
          company={form.company}
          excludeId={Number(id)}
        />
      )}
    />
  );
}
