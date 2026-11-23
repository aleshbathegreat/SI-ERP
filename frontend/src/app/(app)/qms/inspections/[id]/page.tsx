"use client";

import EntityFormRoute from "@/components/crud/EntityFormRoute";
import { useQmsActions } from "@/components/qms/useQmsActions";
import { getEntityDef } from "@/lib/entityCrudDefs";
import { Typography } from "@mui/material";
import { useParams } from "next/navigation";

const def = getEntityDef("qms/inspections")!;

export default function Page() {
  const params = useParams();
  const id = String(params.id);
  const { raiseNcrButton } = useQmsActions();

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
        <>
          <Typography variant="body2" color="text.secondary" sx={{ mr: 1 }}>
            Pass releases inspected quantity. Fail keeps it in quarantine.
          </Typography>
          {raiseNcrButton({ ...form, id: Number(id) })}
        </>
      )}
    />
  );
}