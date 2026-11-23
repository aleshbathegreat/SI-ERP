"use client";

import { useState } from "react";
import { Button, Chip, MenuItem, Stack, TextField } from "@mui/material";
import { useRouter } from "next/navigation";
import { useSnackbar } from "notistack";
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
  return_type: string;
  period_start: string;
  period_end: string;
  status: string;
  totals?: Record<string, string | number | undefined>;
};

const moduleKey = "finance.tax_returns";
const basePath = "/finance/tax-returns";
const apiPath = "/finance/tax-returns/";

function monthStart() {
  const d = new Date();
  return new Date(d.getFullYear(), d.getMonth(), 1).toLocaleDateString("en-CA");
}

export default function Page() {
  const { canAdd, canChange, canDelete } = usePermissions();
  const router = useRouter();
  const crud = useCrudList<Row>(apiPath, "Tax return", basePath);
  const { enqueueSnackbar } = useSnackbar();
  const [type, setType] = useState("sales_tax");
  const [start, setStart] = useState(monthStart());
  const [end, setEnd] = useState(new Date().toLocaleDateString("en-CA"));
  const [busy, setBusy] = useState(false);

  const generate = async () => {
    setBusy(true);
    try {
      const { data } = await api.post<Row>(`${apiPath}generate/`, {
        return_type: type,
        period_start: start,
        period_end: end,
      });
      enqueueSnackbar("Tax return generated from invoices / challans", {
        variant: "success",
      });
      router.push(`${basePath}/${data.id}`);
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Generate failed"), errorSnackbarOpts);
    } finally {
      setBusy(false);
    }
  };

  return (
    <ModuleGate module={moduleKey}>
      <>
        <Stack
          direction="row"
          spacing={1}
          mb={2}
          alignItems="center"
          flexWrap="wrap"
          useFlexGap
        >
          <TextField
            select
            size="small"
            label="Return type"
            value={type}
            onChange={(e) => setType(e.target.value)}
            sx={{ minWidth: 180 }}
          >
            <MenuItem value="sales_tax">Sales tax</MenuItem>
            <MenuItem value="wht">Withholding tax</MenuItem>
          </TextField>
          <TextField
            size="small"
            type="date"
            label="Period start"
            InputLabelProps={{ shrink: true }}
            value={start}
            onChange={(e) => setStart(e.target.value)}
          />
          <TextField
            size="small"
            type="date"
            label="Period end"
            InputLabelProps={{ shrink: true }}
            value={end}
            onChange={(e) => setEnd(e.target.value)}
          />
          <Button
            variant="contained"
            disabled={!canAdd(moduleKey) || busy}
            onClick={generate}
          >
            Generate return
          </Button>
        </Stack>
        <CrudTable
          title="Tax returns"
          subtitle="Sales tax / WHT returns built from AR invoices, AP WHT and tax challans"
          rows={crud.rows}
          loading={crud.loading}
          selectedIds={crud.selectedIds}
          onToggleAll={crud.toggleAll}
          onToggleOne={crud.toggleOne}
          onRefresh={crud.load}
          onCreate={() => undefined}
          onEdit={(row) => router.push(`${basePath}/${row.id}`)}
          onView={(row) => router.push(`${basePath}/${row.id}`)}
          onDeleteOne={crud.askDeleteOne}
          onBulkDelete={crud.askBulkDelete}
          canCreate={false}
          canEdit={canChange(moduleKey)}
          canDelete={canDelete(moduleKey)}
          emptyTitle="No tax returns yet"
          emptyHint="Pick a type and period, then Generate return."
          columns={[
            {
              key: "return_type",
              header: "Type",
              render: (r) => (
                <Chip
                  size="small"
                  variant="outlined"
                  label={r.return_type === "wht" ? "WHT" : "Sales tax"}
                />
              ),
            },
            {
              key: "period",
              header: "Period",
              render: (r) =>
                `${formatDate(r.period_start)} → ${formatDate(r.period_end)}`,
            },
            {
              key: "tax_total",
              header: "Tax",
              render: (r) => formatMoney(r.totals?.tax_total ?? 0),
            },
            {
              key: "deposited",
              header: "Deposited",
              render: (r) => formatMoney(r.totals?.deposited ?? 0),
            },
            {
              key: "net_payable",
              header: "Net payable",
              render: (r) => formatMoney(r.totals?.net_payable ?? 0),
            },
            {
              key: "status",
              header: "Status",
              render: (r) => (
                <Chip
                  size="small"
                  variant="outlined"
                  color={r.status === "filed" ? "success" : "default"}
                  label={r.status}
                />
              ),
            },
          ]}
        />
        <ConfirmDialog
          open={!!crud.confirm}
          title="Delete tax return?"
          message="Draft returns only. This cannot be undone."
          confirmLabel="Delete"
          loading={crud.saving}
          onClose={() => crud.setConfirm(null)}
          onConfirm={crud.runConfirmDelete}
        />
      </>
    </ModuleGate>
  );
}
