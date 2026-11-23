"use client";

import { Button } from "@mui/material";
import EntityFormRoute from "@/components/crud/EntityFormRoute";
import { usePermissions } from "@/hooks/usePermissions";
import { useRecordAction } from "@/hooks/useRecordAction";
import { getEntityDef } from "@/lib/entityCrudDefs";
import { useParams } from "next/navigation";

const def = getEntityDef("mfg/work-orders")!;

export default function Page() {
  const params = useParams();
  const id = String(params.id);
  const { canChange } = usePermissions();
  const { run, busy } = useRecordAction();

  const act = (action: "release" | "complete" | "cancel", reload: () => void) =>
    run(`${action}-${id}`, `${def.apiPath}${id}/${action}/`, {
      success:
        action === "release"
          ? "Work order released"
          : action === "complete"
            ? "Work order completed"
            : "Work order cancelled",
      onDone: reload,
    });

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
      viewActions={({ form, reload }) => {
        if (!canChange(def.moduleKey)) return null;
        const status = String(form.status ?? "");
        return (
          <>
            {status === "draft" ? (
              <Button
                variant="contained"
                color="secondary"
                disabled={busy}
                onClick={() => void act("release", reload)}
              >
                Release
              </Button>
            ) : null}
            {status === "released" || status === "in_progress" ? (
              <Button
                variant="contained"
                color="success"
                disabled={busy}
                onClick={() => void act("complete", reload)}
              >
                Complete
              </Button>
            ) : null}
            {["draft", "released", "in_progress"].includes(status) ? (
              <Button variant="outlined" color="error" disabled={busy} onClick={() => void act("cancel", reload)}>
                Cancel WO
              </Button>
            ) : null}
          </>
        );
      }}
    />
  );
}
