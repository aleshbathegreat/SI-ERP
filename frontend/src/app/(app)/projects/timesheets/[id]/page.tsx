"use client";

import Link from "next/link";
import { Button } from "@mui/material";
import EntityFormRoute from "@/components/crud/EntityFormRoute";
import { DetailSection } from "@/components/crud/DetailPageShell";
import { useTimesheetActions } from "@/components/projects/useTimesheetActions";
import { getEntityDef } from "@/lib/entityCrudDefs";
import { useParams } from "next/navigation";

const def = getEntityDef("projects/timesheets")!;

export default function Page() {
  const params = useParams();
  const id = String(params.id);
  const { actionButtons } = useTimesheetActions();

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
      viewTitleField="date"
      viewActions={({ form, reload }) => actionButtons(Number(id), form.status, reload)}
      viewExtra={({ form }) => {
        const invoiceId = form.customer_invoice ? Number(form.customer_invoice) : null;
        if (!invoiceId) return null;
        return (
          <DetailSection title="Billing" collapsible={false}>
            <Button component={Link} href={`/sales/invoices/${invoiceId}`} size="small">
              {String(form.invoice_no || "AR invoice")}
            </Button>
          </DetailSection>
        );
      }}
    />
  );
}
