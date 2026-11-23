"use client";

import { useParams } from "next/navigation";
import EntityFormRoute from "@/components/crud/EntityFormRoute";
import { getEntityDef } from "@/lib/entityCrudDefs";
import { DocumentActions } from "../DocumentActions";
import { DocumentWorkspace } from "../DocumentWorkspace";
import { DocumentWorkflow, DocumentWorkflowPanel } from "../WorkflowPreview";

const def = getEntityDef("dms/documents")!;

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
      viewTitleField="title"
      viewActions={({ form, reload }) => (
        <DocumentActions
          id={id}
          status={String(form.status || "")}
          checkedOut={Boolean(form.checked_out_by_name)}
          workflow={form.workflow}
          onDone={reload}
        />
      )}
      viewExtra={({ form, reload }) => (
        <>
          <DocumentWorkflowPanel
            id={id}
            workflow={(form.workflow as DocumentWorkflow) || null}
            onDone={reload}
          />
          <DocumentWorkspace id={id} form={form} onDone={reload} />
        </>
      )}
    />
  );
}
