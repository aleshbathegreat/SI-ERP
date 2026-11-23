"use client";

import { useEffect, useState } from "react";
import { Button, Chip, Stack, TextField } from "@mui/material";
import CrudTable from "@/components/crud/CrudTable";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import ModuleGate from "@/components/ModuleGate";
import PageHeader from "@/components/PageHeader";
import { useCrudController } from "@/hooks/useCrudController";
import { usePermissions } from "@/hooks/usePermissions";
import api from "@/lib/api";
import { useSnackbar } from "notistack";

type Row = {
  id: number;
  challan_no: string;
  tax_type: string;
  period_label: string;
  amount: string | number;
  status: string;
};

export default function ChallansPage() {
  const moduleKey = "finance.tax";
  const { canAdd, canChange, canDelete } = usePermissions();
  const crud = useCrudController<Row>("/finance/tax-challans/", "Tax challan");
  const { enqueueSnackbar } = useSnackbar();
  const [period, setPeriod] = useState(new Date().toISOString().slice(0, 7));

  useEffect(() => {
    crud.load();
  }, []);

  return (
    <ModuleGate module={moduleKey}>
      <PageHeader
        title="Tax Challans"
        subtitle="Roll up WHT from approved/paid AP into FBR-ready challans · CSV export"
        moduleKey={moduleKey}
      />
      <Stack direction="row" spacing={1} mb={2} alignItems="center" flexWrap="wrap" useFlexGap>
        <TextField
          size="small"
          label="Tax period"
          value={period}
          helperText="YYYY-MM"
          onChange={(e) => setPeriod(e.target.value)}
        />
        <Button
          variant="contained"
          disabled={!canAdd(moduleKey)}
          onClick={async () => {
            try {
              await api.post("/finance/tax-challans/generate-wht/", { period_label: period });
              enqueueSnackbar("WHT challan generated from AP", { variant: "success" });
              crud.load();
            } catch {
              enqueueSnackbar("Generate failed", { variant: "error" });
            }
          }}
        >
          Generate WHT from AP
        </Button>
      </Stack>
      <CrudTable
        title="Challans"
        rows={crud.rows}
        loading={crud.loading}
        selectedIds={crud.selectedIds}
        onToggleAll={crud.toggleAll}
        onToggleOne={crud.toggleOne}
        onRefresh={crud.load}
        onCreate={() => undefined}
        onEdit={() => undefined}
        onView={async (row) => {
          window.open(
            `${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api"}/finance/tax-challans/${row.id}/export_csv/`,
            "_blank"
          );
        }}
        onDeleteOne={crud.askDeleteOne}
        onBulkDelete={crud.askBulkDelete}
        canCreate={false}
        canEdit={canChange(moduleKey)}
        canDelete={canDelete(moduleKey)}
        columns={[
          { key: "no", header: "Challan", render: (r) => r.challan_no },
          { key: "type", header: "Type", render: (r) => r.tax_type },
          { key: "period", header: "Period", render: (r) => r.period_label },
          { key: "amount", header: "Amount", render: (r) => r.amount },
          {
            key: "status",
            header: "Status",
            render: (r) => <Chip size="small" label={r.status} variant="outlined" />,
          },
        ]}
      />
      <ConfirmDialog
        open={!!crud.confirm}
        title={
          crud.confirm?.type === "bulk" ? "Delete selected challans?" : "Delete challan?"
        }
        message={
          crud.confirm?.type === "bulk"
            ? `Permanently delete ${crud.selectedIds.length} challan(s)?`
            : `Delete challan “${crud.confirm?.row?.challan_no}”?`
        }
        confirmLabel="Delete"
        loading={crud.saving}
        onClose={() => crud.setConfirm(null)}
        onConfirm={crud.runConfirmDelete}
      />
    </ModuleGate>
  );
}
