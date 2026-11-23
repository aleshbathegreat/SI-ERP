"use client";

import { useMemo, useState } from "react";
import {
  Box,
  Button,
  Chip,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import CrudTable from "@/components/crud/CrudTable";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import ModuleGate from "@/components/ModuleGate";
import { useCrudList } from "@/hooks/useCrudList";
import { usePermissions } from "@/hooks/usePermissions";
import { formatDate, formatMoney } from "@/lib/format";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { useSnackbar } from "notistack";
import { useRouter } from "next/navigation";

type Row = {
  id: number;
  quote_no: string;
  customer_name?: string;
  quote_date: string;
  amount: number | string;
  currency?: string;
  status: string;
  sales_order_no?: string;
};

const moduleKey = "sales.quotes";
const basePath = "/sales/quotes";
const apiPath = "/sales/quotes/";

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <Box sx={{ flex: 1, minWidth: 100, px: 1.5, py: 1, borderBottom: "2px solid", borderColor: "divider" }}>
      <Typography variant="caption" color="text.secondary">{label}</Typography>
      <Typography variant="h6" fontWeight={700}>{value}</Typography>
    </Box>
  );
}

export default function Page() {
  const { canAdd, canChange, canDelete } = usePermissions();
  const crud = useCrudList<Row>(apiPath, "Quotation", basePath);
  const [statusFilter, setStatusFilter] = useState("all");
  const { enqueueSnackbar } = useSnackbar();
  const router = useRouter();
  const [busyId, setBusyId] = useState<number | null>(null);

  const filtered = useMemo(() => {
    if (statusFilter === "all") return crud.rows;
    return crud.rows.filter((r) => r.status === statusFilter);
  }, [crud.rows, statusFilter]);

  const kpis = useMemo(() => {
    const rows = crud.rows;
    return {
      total: rows.length,
      draft: rows.filter((r) => r.status === "draft").length,
      sent: rows.filter((r) => r.status === "sent").length,
      converted: rows.filter((r) => r.status === "converted").length,
    };
  }, [crud.rows]);

  const convert = async (id: number) => {
    setBusyId(id);
    try {
      const { data } = await api.post<{ sales_order_id: number; order_no: string }>(
        `${apiPath}${id}/convert/`
      );
      enqueueSnackbar(`Converted to ${data.order_no}`, { variant: "success" });
      router.push(`/sales/orders/${data.sales_order_id}`);
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Convert failed"), errorSnackbarOpts);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <ModuleGate module={moduleKey}>
      <Box>
        {!crud.loading && crud.rows.length > 0 ? (
          <Stack direction="row" flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
            <Kpi label="Quotes" value={String(kpis.total)} />
            <Kpi label="Draft" value={String(kpis.draft)} />
            <Kpi label="Sent" value={String(kpis.sent)} />
            <Kpi label="Converted" value={String(kpis.converted)} />
          </Stack>
        ) : null}
        <ToggleButtonGroup exclusive size="small" value={statusFilter} onChange={(_, v) => v && setStatusFilter(v)} sx={{ mb: 2, flexWrap: "wrap" }}>
          {["all", "draft", "sent", "accepted", "converted", "cancelled"].map((v) => (
            <ToggleButton key={v} value={v}>{v === "all" ? "All" : v}</ToggleButton>
          ))}
        </ToggleButtonGroup>
        <CrudTable
          title="Quotations"
          subtitle="Price offers · accept · convert to sales order"
          rows={filtered}
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
          createLabel="New quotation"
          canCreate={canAdd(moduleKey)}
          canEdit={canChange(moduleKey)}
          canDelete={canDelete(moduleKey)}
          emptyTitle="No quotations"
          emptyHint="Create a quote, send it, then convert to a sales order."
          columns={[
            { key: "quote_no", header: "Quote", render: (r) => r.quote_no || "—" },
            { key: "customer_name", header: "Customer", render: (r) => r.customer_name || "—" },
            { key: "quote_date", header: "Date", render: (r) => formatDate(r.quote_date) },
            {
              key: "amount",
              header: "Amount",
              render: (r) => `${formatMoney(Number(r.amount || 0))} ${r.currency || ""}`.trim(),
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
                ["draft", "sent", "accepted"].includes(r.status) && canChange(moduleKey) ? (
                  <Button
                    size="small"
                    variant="contained"
                    disabled={busyId === r.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      convert(r.id);
                    }}
                  >
                    Convert to SO
                  </Button>
                ) : r.sales_order_no ? (
                  <Typography variant="caption">{r.sales_order_no}</Typography>
                ) : null,
            },
          ]}
        />
        <ConfirmDialog
          open={!!crud.confirm}
          title="Delete quotation?"
          message="This cannot be undone."
          confirmLabel="Delete"
          loading={crud.saving}
          onClose={() => crud.setConfirm(null)}
          onConfirm={crud.runConfirmDelete}
        />
      </Box>
    </ModuleGate>
  );
}
