"use client";

import { useParams } from "next/navigation";
import EntityFormRoute from "@/components/crud/EntityFormRoute";
import { getEntityDef } from "@/lib/entityCrudDefs";
import { WorkflowDesk } from "../WorkflowDesk";

const def = getEntityDef("dms/workflows")!;

export default function Page() {
  const params = useParams();
  const id = String(params.id);
  return (
    <EntityFormRoute
      moduleKey={def.moduleKey}
      resourcePath={def.apiPath}
      entityLabel={def.entityLabel}
      basePath={`/${def.route}`}
      mode="view"
      id={id}
      fields={def.fields}
      empty={def.empty}
      viewTitleField="name"
      viewExtra={({ form, reload }) => <WorkflowDesk id={id} form={form} onDone={reload} />}
    />
  );
}
