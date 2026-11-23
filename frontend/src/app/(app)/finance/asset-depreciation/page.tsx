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
  period_year: number;
  period_month: number;
  status: string;
  posted_at?: string;
};

const moduleKey = "finance.assets";
const basePath = "/finance/asset-depreciation";
const apiPath = "/finance/asset-depreciation/";

export default function Page() {
  const { canAdd, canChange, canDelete } = usePermissions();
  const crud = useCrudList<Row>(apiPath, "Depreciation run", basePath);
  const { enqueueSnackbar } = useSnackbar();
  const [busyId, setBusyId] = useState<number | null>(null);

  const postRun = async (id: number) => {
    setBusyId(id);
    try {
      const { data } = await api.post<{ posted_assets: number; errors?: string[] }>(
        `${apiPath}${id}/post/`
      );
      enqueueSnackbar(
        `Posted ${data.posted_assets} asset(s)${data.errors?.length ? ` · ${data.errors.length} GL warning(s)` : ""}`,
        { variant: data.errors?.length ? "warning" : "success" }
      );
      await crud.load();
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Post failed"), errorSnackbarOpts);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <ModuleGate module={moduleKey}>
      <>
        <CrudTable
          title="Asset depreciation"
          subtitle="Monthly runs · posts JE via GL automation"
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
          createLabel="New run"
          canCreate={canAdd(moduleKey)}
          canEdit={canChange(moduleKey)}
          canDelete={canDelete(moduleKey)}
          emptyTitle="No depreciation runs"
          emptyHint="Create a period run, then post to depreciate active assets."
          columns={[
            { key: "period_year", header: "Year", render: (r) => String(r.period_year) },
            { key: "period_month", header: "Month", render: (r) => String(r.period_month) },
            {
              key: "status",
              header: "Status",
              render: (r) => <Chip size="small" label={r.status} variant="outlined" />,
            },
            {
              key: "posted_at",
              header: "Posted",
              render: (r) => formatDate(r.posted_at),
            },
            {
              key: "actions",
              header: "",
              render: (r) =>
                r.status === "draft" && canChange(moduleKey) ? (
                  <Button
                    size="small"
                    variant="contained"
                    disabled={busyId === r.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      postRun(r.id);
                    }}
                  >
                    Post
                  </Button>
                ) : null,
            },
          ]}
        />
        <ConfirmDialog
          open={!!crud.confirm}
          title="Delete run?"
          message="Only draft runs should be deleted."
          confirmLabel="Delete"
          loading={crud.saving}
          onClose={() => crud.setConfirm(null)}
          onConfirm={crud.runConfirmDelete}
        />
      </>
    </ModuleGate>
  );
}
