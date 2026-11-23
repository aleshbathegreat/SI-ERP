"use client";

import EntityFormRoute from "@/components/crud/EntityFormRoute";
import SparePartsPanel from "@/components/inventory/SparePartsPanel";
import { useServiceActions } from "@/components/service/useServiceActions";
import { usePermissions } from "@/hooks/usePermissions";
import { getEntityDef } from "@/lib/entityCrudDefs";
import { useParams } from "next/navigation";

const def = getEntityDef("service/cases")!;

export default function Page() {
  const params = useParams();
  const id = String(params.id);
  const { actionButtons } = useServiceActions();
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
      viewActions={({ form, reload }) => (
        <>{actionButtons(Number(id), { ...form, id: Number(id) }, reload)}</>
      )}
      viewExtra={({ form, reload }) => {
        const status = String(form.status ?? "");
        const parts = Array.isArray(form.parts) ? form.parts : [];
        return (
          <SparePartsPanel
            lines={parts}
            canIssue={canChange(def.moduleKey) && status !== "closed" && !form.customer_invoice}
            issueUrl={`/service/cases/${id}/issue-part/`}
            onChanged={reload}
            showPrice
            canInvoice={
              canChange(def.moduleKey) &&
              (status === "resolved" || status === "closed") &&
              !form.customer_invoice &&
              !!form.customer
            }
            invoiceUrl={`/service/cases/${id}/create-invoice/`}
            invoiceId={form.customer_invoice ? Number(form.customer_invoice) : null}
            invoiceNo={String(form.invoice_no ?? "")}
          />
        );
      }}
    />
  );
}