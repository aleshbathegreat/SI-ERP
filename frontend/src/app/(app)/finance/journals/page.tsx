"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import CrudTable from "@/components/crud/CrudTable";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import WorkflowActions from "@/components/WorkflowActions";
import { useCrudList } from "@/hooks/useCrudList";
import { usePermissions } from "@/hooks/usePermissions";
import ModuleGate from "@/components/ModuleGate";
import { formatDate, formatMoney } from "@/lib/format";
import { humanizeStatus } from "@/lib/financeLabels";

type Journal = {
  id: number;
  entry_date: string;
  reference: string;
  narration: string;
  status: string;
  total_debit?: number;
  total_credit?: number;
  balanced?: boolean;
};

const moduleKey = "finance.journals";
const basePath = "/finance/journals";

const statusColor = (s: string): "default" | "info" | "warning" | "success" | "error" => {
  if (s === "draft") return "default";
  if (s === "submitted") return "info";
  if (s === "approved") return "warning";
  if (s === "posted") return "success";
  if (s === "rejected") return "error";
  return "default";
};

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <Card variant="outlined" sx={{ flex: 1, minWidth: 120 }}>
      <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
        <Typography variant="caption" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="h6" fontWeight={700}>
          {value}
        </Typography>
      </CardContent>
    </Card>
  );
}

export default function JournalsPage() {
  const { canAdd, canChange, canDelete } = usePermissions();
  const crud = useCrudList<Journal>("/finance/journals/", "Journal entry", basePath);
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const filtered = useMemo(() => {
    if (statusFilter === "all") return crud.rows;
    return crud.rows.filter((r) => r.status === statusFilter);
  }, [crud.rows, statusFilter]);

  const kpis = useMemo(() => {
    const rows = crud.rows;
    return {
      total: rows.length,
      draft: rows.filter((r) => r.status === "draft").length,
      pipeline: rows.filter((r) =>
        ["submitted", "approved"].includes(r.status)
      ).length,
      posted: rows.filter((r) => r.status === "posted").length,
      unbalanced: rows.filter((r) => r.balanced === false).length,
    };
  }, [crud.rows]);

  return (
    <ModuleGate module={moduleKey}>
      <Box>
        {!crud.loading && crud.rows.length > 0 ? (
          <Stack direction="row" spacing={1.5} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
            <Kpi label="Journal entries" value={String(kpis.total)} />
            <Kpi label="Draft" value={String(kpis.draft)} />
            <Kpi label="Waiting" value={String(kpis.pipeline)} />
            <Kpi label="Posted" value={String(kpis.posted)} />
            {kpis.unbalanced > 0 ? (
              <Kpi label="Unbalanced" value={String(kpis.unbalanced)} />
            ) : null}
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
            ["posted", "Posted"],
            ["rejected", "Rejected"],
          ].map(([v, label]) => (
            <ToggleButton key={v} value={v}>
              {label}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>

        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
          {[
            ["/finance/journals/new", "Journal entry"],
            ["/finance/invoices/new", "Bill"],
            ["/sales/invoices/new", "Invoice"],
            ["/sales/invoices", "Customer payment"],
            ["/finance/vendors/new", "Vendor"],
            ["/sales/customers/new", "Customer"],
            ["/finance/accounts", "Chart of accounts"],
            ["/finance/reports", "Profit and loss"],
            ["/finance/reconciliations", "Reconcile"],
          ].map(([href, label]) => (
            <Button key={href} component={Link} href={href} size="small" variant="outlined">
              {label}
            </Button>
          ))}
        </Stack>

        <CrudTable
          title="Journal entries"
          subtitle="Debit and credit lines for each account. The two sides must match before the entry can be saved."
          rows={filtered}
          loading={crud.loading}
          selectedIds={crud.selectedIds}
          onToggleAll={crud.toggleAll}
          onToggleOne={crud.toggleOne}
          onRefresh={crud.load}
          onCreate={crud.openCreate}
          onEdit={(r) => {
            if (r.status === "posted" || r.status === "submitted" || r.status === "approved") {
              crud.openView(r);
              return;
            }
            crud.openEdit(r);
          }}
          onView={crud.openView}
          onDeleteOne={crud.askDeleteOne}
          onBulkDelete={crud.askBulkDelete}
          createLabel="New journal entry"
          canCreate={canAdd(moduleKey)}
          canEdit={canChange(moduleKey)}
          canDelete={canDelete(moduleKey)}
          emptyTitle="No journal entries yet"
          emptyHint="Enter the accounts, debits, and credits. A draft can be sent for approval."
          columns={[
            { key: "date", header: "Date", render: (r) => formatDate(r.entry_date) },
            {
              key: "ref",
              header: "Reference",
              render: (r) => r.reference || "—",
            },
            {
              key: "narr",
              header: "Memo",
              render: (r) => r.narration || "—",
            },
            {
              key: "debit",
              header: "Debit",
              render: (r) =>
                r.total_debit != null ? formatMoney(r.total_debit) : "—",
            },
            {
              key: "bal",
              header: "Balanced",
              render: (r) =>
                r.balanced == null ? (
                  "—"
                ) : (
                  <Chip
                    size="small"
                    color={r.balanced ? "success" : "error"}
                    label={r.balanced ? "Yes" : "No"}
                  />
                ),
            },
            {
              key: "status",
              header: "Status",
              render: (r) => (
                <Stack spacing={0.5}>
                  <Chip
                    size="small"
                    color={statusColor(r.status)}
                    label={humanizeStatus(r.status)}
                  />
                  <WorkflowActions
                    resourcePath="/finance/journals/"
                    id={r.id}
                    status={r.status}
                    moduleKey={moduleKey}
                    allowPost
                    onDone={(updated) => {
                      if (updated?.status) crud.patchRow(r.id, { status: updated.status });
                    }}
                  />
                </Stack>
              ),
            },
          ]}
        />
        <ConfirmDialog
          open={!!crud.confirm}
          title={crud.confirm?.type === "bulk" ? "Delete selected journals?" : "Delete journal?"}
          message={
            crud.confirm?.type === "bulk"
              ? `Permanently delete ${crud.selectedIds.length} journal(s)?`
              : `Delete journal ${crud.confirm?.row?.reference || crud.confirm?.row?.id}?`
          }
          confirmLabel="Delete"
          loading={crud.saving}
          onClose={() => crud.setConfirm(null)}
          onConfirm={crud.runConfirmDelete}
        />
      </Box>
    </ModuleGate>
  );
}
