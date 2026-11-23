"use client";

import { useState } from "react";
import { Button, Stack, Typography } from "@mui/material";
import { useSnackbar } from "notistack";
import CrudTable from "@/components/crud/CrudTable";
import ConfirmDialog from "@/components/crud/ConfirmDialog";
import ModuleGate from "@/components/ModuleGate";
import PageHeader from "@/components/PageHeader";
import { useCrudList } from "@/hooks/useCrudList";
import { usePermissions } from "@/hooks/usePermissions";
import api from "@/lib/api";

type Row = {
  id: number;
  employee: number;
  leave_type: number;
  year: number;
  opening: string | number;
  accrued: string | number;
  used: string | number;
  encashed: string | number;
  carried_forward: string | number;
  available?: string | number;
  employee_name?: string;
  leave_type_name?: string;
  leave_type_code?: string;
  allow_encashment?: boolean;
};

const accrueYearDefault = String(new Date().getFullYear());

export default function LeaveBalancesPage() {
  const moduleKey = "hr.leaves";
  const { canAdd, canChange, canDelete } = usePermissions();
  const crud = useCrudList<Row>("/hr/leave-balances/", "Leave balance", "/hr/leave-balances");
  const { enqueueSnackbar } = useSnackbar();
  const [accruing, setAccruing] = useState(false);
  const [carrying, setCarrying] = useState(false);

  const accrueYear = async () => {
    setAccruing(true);
    try {
      const { data } = await api.post("/hr/leave-balances/accrue-year/", {
        year: Number(accrueYearDefault),
      });
      enqueueSnackbar(
        `Accrued year ${data.year}: created ${data.created} balance row(s)`,
        { variant: "success" }
      );
      await crud.load();
    } catch (e: unknown) {
      const detail =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Accrue failed";
      enqueueSnackbar(detail, { variant: "error" });
    } finally {
      setAccruing(false);
    }
  };

  const carryForward = async () => {
    setCarrying(true);
    try {
      const fromYear = Number(accrueYearDefault) - 1;
      const { data } = await api.post("/hr/leave-balances/carry-forward/", {
        from_year: fromYear,
      });
      enqueueSnackbar(
        `Carry-forward ${data.from_year}→${data.to_year}: moved ${data.moved}, skipped ${data.skipped}`,
        { variant: "success" }
      );
      await crud.load();
    } catch (e: unknown) {
      const detail =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Carry-forward failed";
      enqueueSnackbar(detail, { variant: "error" });
    } finally {
      setCarrying(false);
    }
  };

  return (
    <ModuleGate module={moduleKey}>
      <PageHeader
        title="Leave balances"
        subtitle="Opening, accrual, used and encashment per employee / year"
        moduleKey={moduleKey}
      />
      <Stack direction="row" spacing={1} sx={{ mb: 2 }} flexWrap="wrap" useFlexGap>
        <Button variant="outlined" disabled={accruing} onClick={accrueYear}>
          Accrue from quotas ({accrueYearDefault})
        </Button>
        <Button variant="outlined" disabled={carrying} onClick={carryForward}>
          Year-end carry-forward
        </Button>
        <Typography variant="body2" color="text.secondary" sx={{ alignSelf: "center" }}>
          Pro-rata on join · CF respects leave-type max carry-forward.
        </Typography>
      </Stack>
      <CrudTable
        title="Leave balances"
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
        canCreate={canAdd(moduleKey)}
        canEdit={canChange(moduleKey)}
        canDelete={canDelete(moduleKey)}
        columns={[
          { key: "employee", header: "Employee", render: (r) => String(r.employee_name ?? r.employee) },
          { key: "type", header: "Type", render: (r) => String(r.leave_type_code || r.leave_type_name || r.leave_type) },
          { key: "year", header: "Year", render: (r) => String(r.year) },
          { key: "opening", header: "Opening", render: (r) => String(r.opening) },
          { key: "accrued", header: "Accrued", render: (r) => String(r.accrued) },
          { key: "used", header: "Used", render: (r) => String(r.used) },
          { key: "encashed", header: "Encashed", render: (r) => String(r.encashed) },
          { key: "available", header: "Available", render: (r) => String(r.available ?? "—") },
        ]}
      />
      <ConfirmDialog
        open={!!crud.confirm}
        title="Delete balance?"
        message="This cannot be undone."
        confirmLabel="Delete"
        loading={crud.saving}
        onClose={() => crud.setConfirm(null)}
        onConfirm={crud.runConfirmDelete}
      />
    </ModuleGate>
  );
}
