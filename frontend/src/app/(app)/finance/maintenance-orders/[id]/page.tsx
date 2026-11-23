"use client";

import EntityFormRoute from "@/components/crud/EntityFormRoute";
import SparePartsPanel from "@/components/inventory/SparePartsPanel";
import { useMaintenanceActions } from "@/components/maintenance/useMaintenanceActions";
import { usePermissions } from "@/hooks/usePermissions";
import { getEntityDef } from "@/lib/entityCrudDefs";
import { useParams } from "next/navigation";

const def = getEntityDef("finance/maintenance-orders")!;

export default function Page() {
  const params = useParams();
  const id = String(params.id);
  const { actionButtons } = useMaintenanceActions();
  const { canChange } = usePermissions();

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
      subtitle={def.formSubtitle}
      viewActions={({ form, reload }) => (
        <>{actionButtons(Number(id), { ...form, id: Number(id) }, reload)}</>
      )}
      viewExtra={({ form, reload }) => {
        const status = String(form.status ?? "");
        const parts = Array.isArray(form.parts) ? form.parts : [];
        return (
          <SparePartsPanel
            lines={parts}
            canIssue={
              canChange(def.moduleKey) && status !== "done" && status !== "cancelled"
            }
            issueUrl={`/finance/maintenance-orders/${id}/issue-part/`}
            onChanged={reload}
          />
        );
      }}
    />
  );
}