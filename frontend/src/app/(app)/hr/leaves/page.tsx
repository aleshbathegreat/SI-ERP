"use client";

import { useMemo } from "react";
import {
  Box,
  Card,
  CardContent,
  Chip,
  Stack,
  Typography,
} from "@mui/material";
import CrudTable from "@/components/crud/CrudTable";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import WorkflowActions from "@/components/WorkflowActions";
import { useCrudList } from "@/hooks/useCrudList";
import { usePermissions } from "@/hooks/usePermissions";
import ModuleGate from "@/components/ModuleGate";
import { formatDate } from "@/lib/format";

type Leave = {
  id: number;
  employee: number;
  leave_type: number;
  employee_name?: string;
  leave_type_name?: string;
  start_date: string;
  end_date: string;
  days: string | number;
  reason: string;
  status: string;
};

const statusColor = (s: string): "default" | "info" | "warning" | "success" | "error" => {
  if (s === "pending") return "warning";
  if (s === "approved") return "success";
  if (s === "rejected") return "error";
  if (s === "cancelled") return "default";
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

export default function LeavesPage() {
  const moduleKey = "hr.leaves";
  const { canAdd, canChange, canDelete } = usePermissions();
  const crud = useCrudList<Leave>("/hr/leave-requests/", "Leave request", "/hr/leaves");

  const kpis = useMemo(() => {
    const rows = crud.rows;
    return {
      total: rows.length,
      pending: rows.filter((r) => r.status === "pending").length,
      approved: rows.filter((r) => r.status === "approved").length,
    };
  }, [crud.rows]);

  return (
    <ModuleGate module={moduleKey}>
      <Box>
        {!crud.loading && crud.rows.length > 0 ? (
          <Stack direction="row" spacing={1.5} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
            <Kpi label="Requests" value={String(kpis.total)} />
            <Kpi label="Pending" value={String(kpis.pending)} />
            <Kpi label="Approved" value={String(kpis.approved)} />
          </Stack>
        ) : null}
        <CrudTable
          title="Leave requests"
          subtitle="Approve and manage leave — full-page CRUD"
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
          createLabel="Add leave request"
          canCreate={canAdd(moduleKey)}
          canEdit={canChange(moduleKey)}
          canDelete={canDelete(moduleKey)}
          emptyTitle="No leave requests"
          emptyHint="Submit a leave request for an employee to begin approval."
          columns={[
            { key: "emp", header: "Employee", render: (r) => r.employee_name || r.employee },
            { key: "type", header: "Type", render: (r) => r.leave_type_name || r.leave_type },
            { key: "from", header: "From", render: (r) => formatDate(r.start_date) },
            { key: "to", header: "To", render: (r) => formatDate(r.end_date) },
            { key: "days", header: "Days", render: (r) => r.days },
            {
              key: "status",
              header: "Status / LoA",
              render: (r) => (
                <Stack spacing={0.5}>
                  <Chip size="small" color={statusColor(r.status)} label={r.status} />
                  <WorkflowActions
                    resourcePath="/hr/leave-requests/"
                    id={r.id}
                    status={r.status}
                    moduleKey={moduleKey}
                    onDone={crud.load}
                  />
                </Stack>
              ),
            },
          ]}
        />
        <ConfirmDialog
          open={!!crud.confirm}
          title={
            crud.confirm?.type === "bulk" ? "Delete selected leave requests?" : "Delete leave request?"
          }
          message={
            crud.confirm?.type === "bulk"
              ? `Permanently delete ${crud.selectedIds.length} leave request(s)?`
              : `Delete leave request for ${crud.confirm?.row?.employee_name || "employee"}?`
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
