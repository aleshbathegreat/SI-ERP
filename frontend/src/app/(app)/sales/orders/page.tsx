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
import OutboxIcon from "@mui/icons-material/Outbox";
import CrudTable from "@/components/crud/CrudTable";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import WorkflowActions from "@/components/WorkflowActions";
import ModuleGate from "@/components/ModuleGate";
import { useCrudList } from "@/hooks/useCrudList";
import { usePermissions } from "@/hooks/usePermissions";
import { formatDate, formatMoney } from "@/lib/format";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { useSnackbar } from "notistack";

type Row = {
  id: number;
  order_no: string;
  customer_name?: string;
  order_date: string;
  expected_date?: string | null;
  amount: number | string;
  currency?: string;
  status: string;
  fulfillment?: { pct?: number; open?: string };
};

const moduleKey = "sales.orders";
const basePath = "/sales/orders";
const apiPath = "/sales/orders/";

const statusColor = (
  s: string
): "default" | "info" | "warning" | "success" | "error" => {
  if (s === "draft") return "default";
  if (s === "confirmed") return "info";
  if (s === "delivered") return "warning";
  if (s === "invoiced") return "success";
  if (s === "cancelled") return "error";
  return "default";
};

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <Box
      sx={{
        flex: 1,
        minWidth: 100,
        px: 1.5,
        py: 1,
        borderBottom: "2px solid",
        borderColor: "divider",
      }}
    >
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="h6" fontWeight={700}>
        {value}
      </Typography>
    </Box>
  );
}

export default function Page() {
  const { canAdd, canChange, canDelete } = usePermissions();
  const crud = useCrudList<Row>(apiPath, "Sales order", basePath);
  const [statusFilter, setStatusFilter] = useState("all");
  const { enqueueSnackbar } = useSnackbar();
  const [busyId, setBusyId] = useState<number | null>(null);

  const filtered = useMemo(() => {
    if (statusFilter === "all") return crud.rows;
    return crud.rows.filter((r) => r.status === statusFilter);
  }, [crud.rows, statusFilter]);

  const kpis = useMemo(() => {
    const rows = crud.rows;
    const openValue = rows
      .filter((r) => ["confirmed"].includes(r.status))
      .reduce((a, r) => a + Number(r.amount || 0), 0);
    return {
      total: rows.length,
      draft: rows.filter((r) => r.status === "draft").length,
      confirmed: rows.filter((r) => r.status === "confirmed").length,
      delivered: rows.filter((r) => r.status === "delivered").length,
      invoiced: rows.filter((r) => r.status === "invoiced").length,
      openValue,
    };
  }, [crud.rows]);

  const deliver = async (id: number) => {
    setBusyId(id);
    try {
      await api.post(`${apiPath}${id}/deliver/`);
      enqueueSnackbar("Goods issued from stock", { variant: "success" });
      crud.load();
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Delivery failed"), errorSnackbarOpts);
    } finally {
      setBusyId(null);
    }
  };

  const createArInvoice = async (id: number) => {
    setBusyId(id);
    try {
      const { data } = await api.post<{ id: number; invoice_no: string }>(
        `${apiPath}${id}/create-invoice/`
      );
      enqueueSnackbar(`AR ${data.invoice_no} created`, { variant: "success" });
      window.location.href = `/sales/invoices/${data.id}`;
    } catch (e: unknown) {
      const err = e as { response?: { data?: { invoice_id?: number } } };
      if (err.response?.data?.invoice_id) {
        window.location.href = `/sales/invoices/${err.response.data.invoice_id}`;
      } else {
        enqueueSnackbar(getApiErrorMessage(e, "Failed"), errorSnackbarOpts);
      }
    } finally {
      setBusyId(null);
    }
  };

  return (
    <ModuleGate module={moduleKey}>
      <Box>
        {!crud.loading && crud.rows.length > 0 ? (
          <Stack direction="row" spacing={0} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
            <Kpi label="Orders" value={String(kpis.total)} />
            <Kpi label="Draft" value={String(kpis.draft)} />
            <Kpi label="Confirmed" value={String(kpis.confirmed)} />
            <Kpi label="Delivered" value={String(kpis.delivered)} />
            <Kpi label="Invoiced" value={String(kpis.invoiced)} />
            <Kpi label="Open value" value={formatMoney(kpis.openValue)} />
          </Stack>
        ) : null}

        <ToggleButtonGroup
          exclusive
          size="small"
          value={statusFilter}
          onChange={(_, v) => v && setStatusFilter(v)}
          sx={{ mb: 2, flexWrap: "wrap" }}
        >
          {[
            ["all", "All"],
            ["draft", "Draft"],
            ["confirmed", "Confirmed"],
            ["delivered", "Delivered"],
            ["invoiced", "Invoiced"],
            ["cancelled", "Cancelled"],
          ].map(([v, label]) => (
            <ToggleButton key={v} value={v}>
              {label}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>

        <CrudTable
          title="Sales orders"
          subtitle="Order-to-cash · confirm → deliver → invoice"
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
          createLabel="New sales order"
          canCreate={canAdd(moduleKey)}
          canEdit={canChange(moduleKey)}
          canDelete={canDelete(moduleKey)}
          emptyTitle="No sales orders"
          emptyHint="Create an order for a customer, confirm it, then deliver from stock."
          columns={[
            { key: "order_no", header: "Order", render: (r) => r.order_no || "—" },
            {
              key: "customer_name",
              header: "Customer",
              render: (r) => r.customer_name || "—",
            },
            {
              key: "order_date",
              header: "Date",
              render: (r) => formatDate(r.order_date),
            },
            {
              key: "expected_date",
              header: "Promise",
              render: (r) => formatDate(r.expected_date),
            },
            {
              key: "amount",
              header: "Amount",
              render: (r) =>
                `${formatMoney(Number(r.amount || 0))} ${r.currency || ""}`.trim(),
            },
            {
              key: "fulfillment",
              header: "Ship %",
              render: (r) =>
                r.fulfillment?.pct != null ? `${r.fulfillment.pct}%` : "—",
            },
            {
              key: "status",
              header: "Status",
              render: (r) => (
                <Chip
                  size="small"
                  color={statusColor(r.status)}
                  label={r.status}
                  variant="outlined"
                />
              ),
            },
            {
              key: "actions",
              header: "",
              render: (r) => (
                <Stack direction="row" spacing={0.5} alignItems="center" flexWrap="wrap">
                  <WorkflowActions
                    resourcePath={apiPath}
                    id={r.id}
                    status={r.status}
                    moduleKey={moduleKey}
                    onDone={crud.load}
                    submitLabel="Confirm"
                    showCancel
                    cancelStatuses={["draft", "confirmed"]}
                  />
                  {r.status === "confirmed" && canChange(moduleKey) ? (
                    <Button
                      size="small"
                      startIcon={<OutboxIcon />}
                      disabled={busyId === r.id}
                      onClick={(e) => {
                        e.stopPropagation();
                        deliver(r.id);
                      }}
                    >
                      Deliver
                    </Button>
                  ) : null}
                  {["confirmed", "delivered", "invoiced"].includes(r.status) &&
                  canChange(moduleKey) ? (
                    <Button
                      size="small"
                      disabled={busyId === r.id}
                      onClick={(e) => {
                        e.stopPropagation();
                        createArInvoice(r.id);
                      }}
                    >
                      AR invoice
                    </Button>
                  ) : null}
                </Stack>
              ),
            },
          ]}
        />
        <ConfirmDialog
          open={!!crud.confirm}
          title="Delete sales order?"
          message="Only draft/cancelled orders can be deleted."
          confirmLabel="Delete"
          loading={crud.saving}
          onClose={() => crud.setConfirm(null)}
          onConfirm={crud.runConfirmDelete}
        />
      </Box>
    </ModuleGate>
  );
}
