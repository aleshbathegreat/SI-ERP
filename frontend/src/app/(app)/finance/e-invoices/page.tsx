"use client";

import { useState } from "react";
import { Button, Chip } from "@mui/material";
import { useSnackbar } from "notistack";
import CrudTable from "@/components/crud/CrudTable";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import ModuleGate from "@/components/ModuleGate";
import { useCrudList } from "@/hooks/useCrudList";
import { usePermissions } from "@/hooks/usePermissions";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { formatDate } from "@/lib/format";

type Row = {
  id: number;
  invoice_no?: string;
  customer_name?: string;
  fbr_status: string;
  fbr_invoice_no?: string;
  provider_ref?: string;
  mode?: string;
  error_message?: string;
  submitted_at?: string;
};

const moduleKey = "finance.einvoice";
const basePath = "/finance/e-invoices";
const apiPath = "/finance/e-invoices/";

export default function Page() {
  const { canAdd, canChange, canDelete } = usePermissions();
  const crud = useCrudList<Row>(apiPath, "E-invoice", basePath);
  const { enqueueSnackbar } = useSnackbar();
  const [busyId, setBusyId] = useState<number | null>(null);

  const submitSandbox = async (id: number) => {
    setBusyId(id);
    try {
      const { data } = await api.post<Row>(`${apiPath}${id}/submit/`);
      enqueueSnackbar(
        data.mode === "live"
          ? "Submitted to FBR"
          : "Submitted (sandbox — not transmitted to FBR)",
        { variant: "success" }
      );
      await crud.load();
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Submit failed"), errorSnackbarOpts);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <ModuleGate module={moduleKey}>
      <>
        <CrudTable
          title="FBR e-invoices"
          subtitle="Drafts auto-created on AR approval · Submit (sandbox) unless FBR_API_URL is configured"
          rows={crud.rows}
          loading={crud.loading}
          selectedIds={crud.selectedIds}
          onToggleAll={crud.toggleAll}
          onToggleOne={crud.toggleOne}
          onRefresh={crud.load}
          onCreate={crud.openCreate}
          onEdit={crud.openEdit}
          onView={crud.openView}
          onDeleteOne={crud.askDeleteOne}
          onBulkDelete={crud.askBulkDelete}
          createLabel="Link AR invoice"
          canCreate={canAdd(moduleKey)}
          canEdit={canChange(moduleKey)}
          canDelete={canDelete(moduleKey)}
          emptyTitle="No e-invoice submissions"
          emptyHint="Approve an AR invoice to auto-create a draft, or link one manually."
          columns={[
            { key: "invoice_no", header: "AR", render: (r) => r.invoice_no || "—" },
            {
              key: "customer_name",
              header: "Customer",
              render: (r) => r.customer_name || "—",
            },
            {
              key: "fbr_status",
              header: "Status",
              render: (r) => (
                <Chip size="small" label={r.fbr_status} variant="outlined" />
              ),
            },
            {
              key: "fbr_invoice_no",
              header: "FBR no",
              render: (r) => r.fbr_invoice_no || "—",
            },
            {
              key: "provider_ref",
              header: "Provider ref",
              render: (r) => r.provider_ref || "—",
            },
            {
              key: "mode",
              header: "Mode",
              render: (r) => r.mode || "—",
            },
            {
              key: "submitted_at",
              header: "Submitted",
              render: (r) => formatDate(r.submitted_at),
            },
            {
              key: "actions",
              header: "",
              render: (r) =>
                ["draft", "pending", "rejected"].includes(r.fbr_status) &&
                canChange(moduleKey) ? (
                  <Button
                    size="small"
                    variant="contained"
                    disabled={busyId === r.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      submitSandbox(r.id);
                    }}
                  >
                    Submit (sandbox)
                  </Button>
                ) : null,
            },
          ]}
        />
        <ConfirmDialog
          open={!!crud.confirm}
          title="Delete submission?"
          message="This cannot be undone."
          confirmLabel="Delete"
          loading={crud.saving}
          onClose={() => crud.setConfirm(null)}
          onConfirm={crud.runConfirmDelete}
        />
      </>
    </ModuleGate>
  );
}
