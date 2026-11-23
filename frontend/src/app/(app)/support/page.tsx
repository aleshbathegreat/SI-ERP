"use client";

import { useState } from "react";
import { Chip } from "@mui/material";
import DoneAllIcon from "@mui/icons-material/DoneAll";
import CrudTable from "@/components/crud/CrudTable";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import { useCrudList } from "@/hooks/useCrudList";
import api from "@/lib/api";
import { useSnackbar } from "notistack";

type Ticket = {
  id: number;
  ticket_no: string;
  subject: string;
  category: string;
  priority: string;
  status: string;
};

const basePath = "/support";

export default function TenantSupportPage() {
  const crud = useCrudList<Ticket>("/support/tickets/", "Ticket", basePath);
  const { enqueueSnackbar } = useSnackbar();
  const [busy, setBusy] = useState(false);
  const [confirmClose, setConfirmClose] = useState<Ticket | null>(null);

  const runClose = async () => {
    if (!confirmClose) return;
    setBusy(true);
    try {
      await api.patch(`/support/tickets/${confirmClose.id}/`, { status: "closed" });
      enqueueSnackbar("Ticket closed", { variant: "success" });
      setConfirmClose(null);
      crud.load();
    } catch {
      enqueueSnackbar("Close failed", { variant: "error" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <CrudTable
        title="Support"
        subtitle="Platform support tickets"
        rows={crud.rows}
        loading={crud.loading}
        selectedIds={crud.selectedIds}
        onToggleAll={crud.toggleAll}
        onToggleOne={crud.toggleOne}
        onRefresh={crud.load}
        onCreate={crud.openCreate}
        onView={crud.openView}
        onDeleteOne={crud.askDeleteOne}
        onBulkDelete={crud.askBulkDelete}
        createLabel="New ticket"
        canEdit={false}
        getRowActions={(row) =>
          row.status !== "closed"
            ? [
                {
                  key: "close",
                  label: "Close ticket",
                  icon: <DoneAllIcon fontSize="small" />,
                  onClick: () => setConfirmClose(row),
                  dividerBefore: true,
                },
              ]
            : []
        }
        columns={[
          { key: "no", header: "Ticket", render: (t) => t.ticket_no },
          { key: "subject", header: "Subject", render: (t) => t.subject },
          { key: "cat", header: "Category", render: (t) => t.category },
          { key: "pri", header: "Priority", render: (t) => t.priority },
          {
            key: "status",
            header: "Status",
            render: (t) => <Chip size="small" label={t.status} />,
          },
        ]}
      />

      <ConfirmDialog
        open={!!crud.confirm}
        title={
          crud.confirm?.type === "bulk" ? "Delete selected tickets?" : "Delete ticket?"
        }
        message={
          crud.confirm?.type === "bulk"
            ? `Permanently delete ${crud.selectedIds.length} ticket(s)?`
            : `Delete ticket “${crud.confirm?.row?.ticket_no}”?`
        }
        confirmLabel="Delete"
        loading={crud.saving}
        onClose={() => crud.setConfirm(null)}
        onConfirm={crud.runConfirmDelete}
      />

      <ConfirmDialog
        open={!!confirmClose}
        title="Close ticket?"
        message={`Close “${confirmClose?.ticket_no} — ${confirmClose?.subject}”?`}
        confirmLabel="Close ticket"
        danger={false}
        loading={busy}
        onClose={() => setConfirmClose(null)}
        onConfirm={runClose}
      />
    </>
  );
}
