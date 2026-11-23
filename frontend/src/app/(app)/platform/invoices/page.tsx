"use client";

import { useState } from "react";
import {
  Chip,
  Typography,
} from "@mui/material";
import PaidIcon from "@mui/icons-material/Paid";
import BlockIcon from "@mui/icons-material/Block";
import CrudTable from "@/components/crud/CrudTable";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import PlatformGate from "@/components/PlatformGate";
import { useCrudList } from "@/hooks/useCrudList";
import { usePlatformCaps } from "@/hooks/usePlatformCaps";
import api from "@/lib/api";
import { useSnackbar } from "notistack";

type Inv = {
  id: number;
  invoice_no: string;
  organization: number;
  organization_name?: string;
  organization_code?: string;
  plan_code: string;
  description: string;
  amount: string;
  tax_amount: string;
  total: string;
  status: string;
  due_date?: string;
};

const basePath = "/platform/invoices";

export default function PlatformInvoicesPage() {
  const crud = useCrudList<Inv>("/platform/invoices/", "Invoice", basePath);
  const { can } = usePlatformCaps();
  const { enqueueSnackbar } = useSnackbar();
  const [confirmAction, setConfirmAction] = useState<{
    type: "paid" | "void" | "bulk_paid" | "bulk_void";
    row?: Inv;
  } | null>(null);
  const [busy, setBusy] = useState(false);

  const runConfirmAction = async () => {
    if (!confirmAction) return;
    setBusy(true);
    try {
      if (confirmAction.type === "paid" && confirmAction.row) {
        await api.post(`/platform/invoices/${confirmAction.row.id}/mark_paid/`);
        enqueueSnackbar("Marked paid", { variant: "success" });
      } else if (confirmAction.type === "void" && confirmAction.row) {
        await api.post(`/platform/invoices/${confirmAction.row.id}/void/`);
        enqueueSnackbar("Invoice voided", { variant: "success" });
      } else if (confirmAction.type === "bulk_paid") {
        for (const id of crud.selectedIds) {
          await api.post(`/platform/invoices/${id}/mark_paid/`);
        }
        enqueueSnackbar(`Marked ${crud.selectedIds.length} paid`, { variant: "success" });
      } else if (confirmAction.type === "bulk_void") {
        for (const id of crud.selectedIds) {
          await api.post(`/platform/invoices/${id}/void/`);
        }
        enqueueSnackbar(`Voided ${crud.selectedIds.length}`, { variant: "success" });
      }
      setConfirmAction(null);
      crud.load();
    } catch {
      enqueueSnackbar("Action failed", { variant: "error" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <PlatformGate capability="invoices">
      <CrudTable
        title="SaaS invoices"
        subtitle="Platform AR · three-dot actions · bulk mark paid / void / delete"
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
        createLabel="New invoice"
        canSelect
        bulkActions={[
          ...(can("invoices.mark_paid")
            ? [
                {
                  key: "paid",
                  label: "Mark paid",
                  icon: <PaidIcon />,
                  onClick: () => setConfirmAction({ type: "bulk_paid" }),
                },
              ]
            : []),
          {
            key: "void",
            label: "Void selected",
            icon: <BlockIcon />,
            onClick: () => setConfirmAction({ type: "bulk_void" }),
          },
        ]}
        getRowActions={(row) => {
          const actions = [];
          if (row.status !== "paid" && row.status !== "void" && can("invoices.mark_paid")) {
            actions.push({
              key: "paid",
              label: "Mark paid",
              icon: <PaidIcon fontSize="small" />,
              onClick: () => setConfirmAction({ type: "paid", row }),
            });
          }
          if (row.status !== "paid" && row.status !== "void") {
            actions.push({
              key: "void",
              label: "Void",
              icon: <BlockIcon fontSize="small" />,
              onClick: () => setConfirmAction({ type: "void", row }),
              danger: true,
              dividerBefore: true,
            });
          }
          return actions;
        }}
        columns={[
          { key: "no", header: "Invoice", render: (r) => r.invoice_no },
          {
            key: "tenant",
            header: "Tenant",
            render: (r) => (
              <>
                {r.organization_name}
                <Typography variant="caption" display="block" color="text.secondary">
                  {r.organization_code}
                </Typography>
              </>
            ),
          },
          { key: "plan", header: "Plan", render: (r) => r.plan_code || "—" },
          { key: "total", header: "Total", render: (r) => r.total },
          { key: "due", header: "Due", render: (r) => r.due_date || "—" },
          {
            key: "status",
            header: "Status",
            render: (r) => (
              <Chip
                size="small"
                color={
                  r.status === "paid"
                    ? "success"
                    : r.status === "overdue"
                      ? "error"
                      : "default"
                }
                label={r.status}
              />
            ),
          },
        ]}
      />

      <ConfirmDialog
        open={!!crud.confirm}
        title={
          crud.confirm?.type === "bulk" ? "Delete selected invoices?" : "Delete invoice?"
        }
        message={
          crud.confirm?.type === "bulk"
            ? `Permanently delete ${crud.selectedIds.length} invoice(s)?`
            : `Delete invoice “${crud.confirm?.row?.invoice_no}”?`
        }
        confirmLabel="Delete"
        loading={crud.saving}
        onClose={() => crud.setConfirm(null)}
        onConfirm={crud.runConfirmDelete}
      />

      <ConfirmDialog
        open={!!confirmAction}
        title={
          confirmAction?.type === "paid" || confirmAction?.type === "bulk_paid"
            ? "Mark invoice(s) paid?"
            : "Void invoice(s)?"
        }
        message={
          confirmAction?.type === "paid"
            ? `Mark “${confirmAction.row?.invoice_no}” as paid?`
            : confirmAction?.type === "void"
              ? `Void “${confirmAction.row?.invoice_no}”?`
              : confirmAction?.type === "bulk_paid"
                ? `Mark ${crud.selectedIds.length} invoice(s) as paid?`
                : `Void ${crud.selectedIds.length} invoice(s)?`
        }
        confirmLabel={
          confirmAction?.type === "paid" || confirmAction?.type === "bulk_paid"
            ? "Mark paid"
            : "Void"
        }
        danger={
          confirmAction?.type === "void" || confirmAction?.type === "bulk_void"
        }
        loading={busy}
        onClose={() => setConfirmAction(null)}
        onConfirm={runConfirmAction}
      />
    </PlatformGate>
  );
}
