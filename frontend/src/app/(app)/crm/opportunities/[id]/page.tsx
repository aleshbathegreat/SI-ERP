"use client";

import { Button } from "@mui/material";
import EntityFormRoute from "@/components/crud/EntityFormRoute";
import RecordActivities from "@/components/crm/RecordActivities";
import { useCrmActions } from "@/components/crm/useCrmActions";
import { usePermissions } from "@/hooks/usePermissions";
import { getEntityDef } from "@/lib/entityCrudDefs";
import { useParams } from "next/navigation";

const def = getEntityDef("crm/opportunities")!;

export default function Page() {
  const params = useParams();
  const id = String(params.id);
  const { createQuoteButton, lostDialog, moveStage, askLost } = useCrmActions();
  const { canChange } = usePermissions();
  const canMove = canChange("crm.opportunities");

  return (
    <>
      {lostDialog}
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
        <>
          {canMove && form.stage !== "won" ? (
            <Button
              variant="outlined"
              onClick={() => void moveStage(Number(id), "won", undefined, reload)}
            >
              Mark won
            </Button>
          ) : null}
          {canMove && form.stage !== "lost" ? (
            <Button color="error" onClick={() => askLost(Number(id), reload)}>
              Mark lost
            </Button>
          ) : null}
          {createQuoteButton(Number(id), form)}
        </>
      )}
      viewExtra={() => <RecordActivities opportunityId={Number(id)} />}
      />
    </>
  );
}
