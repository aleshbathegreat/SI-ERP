"use client";

import EntityFormRoute from "@/components/crud/EntityFormRoute";
import { useQmsActions } from "@/components/qms/useQmsActions";
import { getEntityDef } from "@/lib/entityCrudDefs";
import { useParams } from "next/navigation";

const def = getEntityDef("qms/ncrs")!;

export default function Page() {
  const params = useParams();
  const id = String(params.id);
  const { closeNcrButton } = useQmsActions();

  return (
    <EntityFormRoute
      moduleKey={def.moduleKey}
      resourcePath={def.apiPath}
      entityLabel={def.entityLabel}
      basePath={"/" + def.route}
      mode="view"
      id={id}
      fields={def.fields}
      empty={def.empty}
      viewActions={({ form, reload }) => (
        <>{closeNcrButton({ ...form, id: Number(id) }, reload)}</>
      )}
    />
  );
}