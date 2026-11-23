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
import { useCrudList } from "@/hooks/useCrudList";
import { usePermissions } from "@/hooks/usePermissions";
import ModuleGate from "@/components/ModuleGate";
import { formatDate, formatMoney } from "@/lib/format";

type Employee = {
  id: number;
  employee_code: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  status: string;
  department: number | null;
  designation: number | null;
  department_name?: string;
  designation_title?: string;
  basic_salary: string | number;
  is_tax_free?: boolean;
  is_attendance_free?: boolean;
  date_of_joining?: string | null;
};

const statusColor = (s: string): "default" | "info" | "warning" | "success" | "error" => {
  if (s === "active") return "success";
  if (s === "probation") return "info";
  if (s === "on_leave") return "warning";
  if (s === "suspended") return "error";
  if (s === "separated") return "default";
  return "default";
};

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <Card variant="outlined" sx={{ flex: 1, minWidth: 140 }}>
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

export default function EmployeesPage() {
  const moduleKey = "hr.employees";
  const { canAdd, canChange, canDelete } = usePermissions();
  const crud = useCrudList<Employee>("/hr/employees/", "Employee", "/hr/employees");

  const kpis = useMemo(() => {
    const rows = crud.rows;
    const active = rows.filter((r) => r.status === "active").length;
    const payroll = rows.reduce((acc, r) => acc + (Number(r.basic_salary) || 0), 0);
    return { total: rows.length, active, payroll };
  }, [crud.rows]);

  return (
    <ModuleGate module={moduleKey}>
      <Box>
        {!crud.loading && crud.rows.length > 0 ? (
          <Stack direction="row" spacing={1.5} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
            <Kpi label="Employees" value={String(kpis.total)} />
            <Kpi label="Active" value={String(kpis.active)} />
            <Kpi label="Basic payroll" value={formatMoney(kpis.payroll)} />
          </Stack>
        ) : null}
        <CrudTable
          title="Employees"
          subtitle="HR master — full-page create, view, and edit"
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
          createLabel="Add employee"
          canCreate={canAdd(moduleKey)}
          canEdit={canChange(moduleKey)}
          canDelete={canDelete(moduleKey)}
          emptyTitle="No employees yet"
          emptyHint="Add an employee record to start HR and payroll."
          columns={[
            { key: "code", header: "Code", render: (r) => r.employee_code },
            {
              key: "name",
              header: "Name",
              render: (r) => `${r.first_name} ${r.last_name}`,
            },
            { key: "email", header: "Email", render: (r) => r.email },
            { key: "dept", header: "Department", render: (r) => r.department_name || "—" },
            { key: "desig", header: "Designation", render: (r) => r.designation_title || "—" },
            {
              key: "salary",
              header: "Basic",
              render: (r) => formatMoney(r.basic_salary),
            },
            {
              key: "payroll_flags",
              header: "Payroll",
              render: (r) =>
                [r.is_tax_free ? "Tax-free" : null, r.is_attendance_free ? "Att-free" : null]
                  .filter(Boolean)
                  .join(" · ") || "—",
            },
            {
              key: "joined",
              header: "Joined",
              render: (r) => formatDate(r.date_of_joining),
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
          ]}
        />
        <ConfirmDialog
          open={!!crud.confirm}
          title={crud.confirm?.type === "bulk" ? "Delete selected employees?" : "Delete employee?"}
          message={
            crud.confirm?.type === "bulk"
              ? `Permanently delete ${crud.selectedIds.length} employee record(s)? This cannot be undone.`
              : `Delete ${crud.confirm?.row?.first_name || ""} ${crud.confirm?.row?.last_name || ""} (${crud.confirm?.row?.employee_code || ""})? This cannot be undone.`
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
