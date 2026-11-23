"use client";

import Link from "next/link";
import { Button } from "@mui/material";
import EntityFormRoute from "@/components/crud/EntityFormRoute";
import LeadDuplicateHint from "@/components/crm/LeadDuplicateHint";
import RecordActivities from "@/components/crm/RecordActivities";
import { useCrmActions } from "@/components/crm/useCrmActions";
import { getEntityDef } from "@/lib/entityCrudDefs";
import { useParams } from "next/navigation";

const def = getEntityDef("crm/leads")!;

export default function Page() {
  const params = useParams();
  const id = String(params.id);
  const { convertLeadButton } = useCrmActions();

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
      viewActions={({ form }) => (
        <>
          {convertLeadButton(Number(id), form)}
          {form.converted_opportunity ? (
            <Button
              component={Link}
              href={`/crm/opportunities/${String(form.converted_opportunity)}`}
              variant="outlined"
            >
              Open opportunity
            </Button>
          ) : null}
        </>
      )}
      viewExtra={({ form }) => (
        <>
          <LeadDuplicateHint
            email={form.email}
            phone={form.phone}
            company={form.company}
            excludeId={Number(id)}
          />
          <RecordActivities leadId={Number(id)} toEmail={String(form.email || "")} />
        </>
      )}
    />
  );
}
