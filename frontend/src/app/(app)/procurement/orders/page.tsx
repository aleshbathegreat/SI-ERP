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
import LocalShippingIcon from "@mui/icons-material/LocalShipping";
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
  po_no: string;
  vendor_name?: string;
  order_date: string;
  expected_date?: string | null;
  amount: number | string;
  currency?: string;
  status: string;
  fulfillment?: { pct?: number; open?: string };
};

const moduleKey = "procurement.orders";
const basePath = "/procurement/orders";
const apiPath = "/procurement/orders/";

const statusColor = (
  s: string
): "default" | "info" | "warning" | "success" | "error" => {
  if (s === "draft") return "default";
  if (s === "submitted") return "info";
  if (s === "approved") return "warning";
  if (s === "received") return "success";
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
  const crud = useCrudList<Row>(apiPath, "Purchase order", basePath);
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
      .filter((r) => ["submitted", "approved"].includes(r.status))
      .reduce((a, r) => a + Number(r.amount || 0), 0);
    return {
      total: rows.length,
      draft: rows.filter((r) => r.status === "draft").length,
      pipeline: rows.filter((r) =>
        ["submitted", "approved"].includes(r.status)
      ).length,
      received: rows.filter((r) => r.status === "received").length,
      openValue,
    };
  }, [crud.rows]);

  const receive = async (id: number) => {
    setBusyId(id);
    try {
      await api.post(`${apiPath}${id}/receive/`);
      enqueueSnackbar("Goods received into stock", { variant: "success" });
      crud.load();
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Receive failed"), errorSnackbarOpts);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <ModuleGate module={moduleKey}>
      <Box>
        {!crud.loading && crud.rows.length > 0 ? (
          <Stack direction="row" spacing={0} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
            <Kpi label="POs" value={String(kpis.total)} />
            <Kpi label="Draft" value={String(kpis.draft)} />
            <Kpi label="In pipeline" value={String(kpis.pipeline)} />
            <Kpi label="Received" value={String(kpis.received)} />
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
            ["submitted", "Submitted"],
            ["approved", "Approved"],
            ["received", "Received"],
            ["cancelled", "Cancelled"],
          ].map(([v, label]) => (
            <ToggleButton key={v} value={v}>
              {label}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>

        <CrudTable
          title="Purchase orders"
          subtitle="Procure-to-pay · submit → approve → GRN → AP invoice"
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
          createLabel="New PO"
          canCreate={canAdd(moduleKey)}
          canEdit={canChange(moduleKey)}
          canDelete={canDelete(moduleKey)}
          emptyTitle="No purchase orders"
          emptyHint="Create a PO against a vendor, submit for approval, then receive goods."
          columns={[
            { key: "po_no", header: "PO", render: (r) => r.po_no || "—" },
            {
              key: "vendor_name",
              header: "Vendor",
              render: (r) => r.vendor_name || "—",
            },
            {
              key: "order_date",
              header: "Date",
              render: (r) => formatDate(r.order_date),
            },
            {
              key: "expected_date",
              header: "Expected",
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
              header: "GRN %",
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
                    showCancel
                    cancelStatuses={["draft", "submitted", "approved"]}
                  />
                  {r.status === "approved" && canChange(moduleKey) ? (
                    <Button
                      size="small"
                      startIcon={<LocalShippingIcon />}
                      disabled={busyId === r.id}
                      onClick={(e) => {
                        e.stopPropagation();
                        receive(r.id);
                      }}
                    >
                      Receive
                    </Button>
                  ) : null}
                </Stack>
              ),
            },
          ]}
        />
        <ConfirmDialog
          open={!!crud.confirm}
          title="Delete purchase order?"
          message="Only draft/cancelled POs can be deleted."
          confirmLabel="Delete"
          loading={crud.saving}
          onClose={() => crud.setConfirm(null)}
          onConfirm={crud.runConfirmDelete}
        />
      </Box>
    </ModuleGate>
  );
}
