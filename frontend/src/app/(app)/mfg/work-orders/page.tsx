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

type Row = {
  id: number;
  wo_no: string;
  item_sku?: string;
  qty_planned: number | string;
  qty_completed: number | string;
  status: string;
};

const moduleKey = "mfg.work_orders";
const basePath = "/mfg/work-orders";
const apiPath = "/mfg/work-orders/";

export default function Page() {
  const { canAdd, canChange, canDelete } = usePermissions();
  const crud = useCrudList<Row>(apiPath, "Work order", basePath);
  const { enqueueSnackbar } = useSnackbar();
  const [busyId, setBusyId] = useState<number | null>(null);

  const act = async (id: number, action: "release" | "complete") => {
    setBusyId(id);
    try {
      const post = (body?: Record<string, unknown>) =>
        api.post(`${apiPath}${id}/${action}/`, body);
      try {
        await post();
      } catch (e: unknown) {
        const msg = getApiErrorMessage(e, "");
        if (action === "complete" && /batch|serial|lot/i.test(msg)) {
          const batch = window.prompt(`${msg}\n\nBatch / lot no (leave blank if serial-tracked):`, "");
          const serials = window.prompt("Serial numbers (comma-separated, blank if none):", "");
          if (batch === null && serials === null) throw e;
          await post({
            batch_no: batch || undefined,
            serial_nos: serials || undefined,
          });
        } else {
          throw e;
        }
      }
      enqueueSnackbar(action === "release" ? "Released" : "Completed", {
        variant: "success",
      });
      await crud.load();
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Action failed"), errorSnackbarOpts);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <ModuleGate module={moduleKey}>
      <>
        <CrudTable
          title="Work orders"
          subtitle="Release · complete (issues components / receipts FG)"
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
          createLabel="New work order"
          canCreate={canAdd(moduleKey)}
          canEdit={canChange(moduleKey)}
          canDelete={canDelete(moduleKey)}
          emptyTitle="No work orders"
          emptyHint="Create a WO against a BOM, release, then complete."
          columns={[
            { key: "wo_no", header: "WO", render: (r) => r.wo_no || "—" },
            { key: "item_sku", header: "Item", render: (r) => r.item_sku || "—" },
            { key: "qty_planned", header: "Planned", render: (r) => String(r.qty_planned ?? "—") },
            { key: "qty_completed", header: "Done", render: (r) => String(r.qty_completed ?? "—") },
            {
              key: "status",
              header: "Status",
              render: (r) => <Chip size="small" label={r.status} variant="outlined" />,
            },
            {
              key: "actions",
              header: "",
              render: (r) =>
                canChange(moduleKey) ? (
                  <>
                    {r.status === "draft" ? (
                      <Button
                        size="small"
                        disabled={busyId === r.id}
                        onClick={(e) => {
                          e.stopPropagation();
                          act(r.id, "release");
                        }}
                      >
                        Release
                      </Button>
                    ) : null}
                    {["released", "in_progress"].includes(r.status) ? (
                      <Button
                        size="small"
                        variant="contained"
                        disabled={busyId === r.id}
                        onClick={(e) => {
                          e.stopPropagation();
                          act(r.id, "complete");
                        }}
                      >
                        Complete
                      </Button>
                    ) : null}
                  </>
                ) : null,
            },
          ]}
        />
        <ConfirmDialog
          open={!!crud.confirm}
          title="Delete work order?"
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
