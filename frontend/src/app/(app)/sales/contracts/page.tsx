"use client";

import { useState } from "react";
import { Button, Chip } from "@mui/material";
import { useSnackbar } from "notistack";
import { useRouter } from "next/navigation";
import CrudTable from "@/components/crud/CrudTable";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import ModuleGate from "@/components/ModuleGate";
import { useCrudList } from "@/hooks/useCrudList";
import { usePermissions } from "@/hooks/usePermissions";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { formatDate, formatMoney } from "@/lib/format";

type Row = {
  id: number;
  name: string;
  customer_name?: string;
  billing_frequency: string;
  amount: number | string;
  next_bill_date?: string;
  status: string;
};

const moduleKey = "sales.contracts";
const basePath = "/sales/contracts";
const apiPath = "/sales/contracts/";

export default function Page() {
  const { canAdd, canChange, canDelete } = usePermissions();
  const crud = useCrudList<Row>(apiPath, "Contract", basePath);
  const { enqueueSnackbar } = useSnackbar();
  const router = useRouter();
  const [busyId, setBusyId] = useState<number | null>(null);

  const generate = async (id: number) => {
    setBusyId(id);
    try {
      const { data } = await api.post<{ invoice_id: number; invoice_no: string }>(
        `${apiPath}${id}/generate-invoice/`
      );
      enqueueSnackbar(`Draft invoice ${data.invoice_no}`, { variant: "success" });
      await crud.load();
      router.push(`/sales/invoices/${data.invoice_id}`);
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Generate failed"), errorSnackbarOpts);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <ModuleGate module={moduleKey}>
      <>
        <CrudTable
          title="Recurring contracts"
          subtitle="Generate draft AR invoices on schedule"
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
          createLabel="Add contract"
          canCreate={canAdd(moduleKey)}
          canEdit={canChange(moduleKey)}
          canDelete={canDelete(moduleKey)}
          emptyTitle="No contracts"
          emptyHint="Create an active contract, then generate invoices."
          columns={[
            { key: "name", header: "Name", render: (r) => r.name || "—" },
            { key: "customer_name", header: "Customer", render: (r) => r.customer_name || "—" },
            {
              key: "billing_frequency",
              header: "Freq",
              render: (r) => (
                <Chip size="small" label={r.billing_frequency} variant="outlined" />
              ),
            },
            {
              key: "amount",
              header: "Amount",
              render: (r) => formatMoney(Number(r.amount || 0)),
            },
            {
              key: "next_bill_date",
              header: "Next bill",
              render: (r) => formatDate(r.next_bill_date),
            },
            {
              key: "status",
              header: "Status",
              render: (r) => <Chip size="small" label={r.status} variant="outlined" />,
            },
            {
              key: "actions",
              header: "",
              render: (r) =>
                r.status === "active" && canChange(moduleKey) ? (
                  <Button
                    size="small"
                    variant="contained"
                    disabled={busyId === r.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      generate(r.id);
                    }}
                  >
                    Generate invoice
                  </Button>
                ) : null,
            },
          ]}
        />
        <ConfirmDialog
          open={!!crud.confirm}
          title="Delete contract?"
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
