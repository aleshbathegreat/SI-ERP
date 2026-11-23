"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Box, Button, Paper, Stack, Typography } from "@mui/material";
import { useSnackbar } from "notistack";
import { DetailSection } from "@/components/crud/DetailPageShell";
import { usePermissions } from "@/hooks/usePermissions";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { formatMoney } from "@/lib/format";

type Summary = {
  budget_amount: string;
  costs_total: string;
  timesheet_hours: string;
  timesheet_amount: string;
  billable_amount: string;
  unbilled_hours: string;
  unbilled_amount: string;
  latest_invoice_id: number | null;
  latest_invoice_no: string;
  total_cost: string;
  budget_remaining: string;
  open_tasks: number;
};

function Metric({ label, value, warn }: { label: string; value: string; warn?: boolean }) {
  return (
    <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 2, minWidth: 150, flex: "1 1 150px" }}>
      <Typography variant="caption" color="text.secondary" sx={{ textTransform: "uppercase" }}>
        {label}
      </Typography>
      <Typography variant="h6" fontWeight={700} color={warn ? "error.main" : undefined}>
        {value}
      </Typography>
    </Paper>
  );
}

export default function ProjectSummaryCard({
  projectId,
  hasCustomer,
}: {
  projectId: string | number;
  hasCustomer: boolean;
}) {
  const { enqueueSnackbar } = useSnackbar();
  const { canChange } = usePermissions();
  const [data, setData] = useState<Summary | null>(null);
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    return api
      .get<Summary>(`/projects/projects/${projectId}/summary/`)
      .then((r) => setData(r.data))
      .catch(() => setError(true));
  }, [projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  const bill = async () => {
    setBusy(true);
    try {
      const { data: created } = await api.post(
        `/projects/projects/${projectId}/bill-timesheets/`,
        {}
      );
      enqueueSnackbar(
        created.invoice_no
          ? `Draft invoice ${created.invoice_no} created`
          : "Draft invoice created",
        { variant: "success" }
      );
      await load();
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Could not create invoice"), errorSnackbarOpts);
    } finally {
      setBusy(false);
    }
  };

  if (error) return null;

  const n = (v?: string) => formatMoney(Number(v || 0));
  const remaining = Number(data?.budget_remaining || 0);
  const unbilled = Number(data?.unbilled_amount || 0);
  const canBill = canChange("projects.projects") && hasCustomer && unbilled > 0;

  return (
    <DetailSection
      title="Job cost summary"
      description="Budget vs project costs and approved timesheets"
      collapsible={false}
    >
      {!data ? (
        <Typography variant="body2" color="text.secondary">
          Loading…
        </Typography>
      ) : (
        <Stack spacing={1.5}>
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1.5 }}>
            <Metric label="Budget" value={n(data.budget_amount)} />
            <Metric label="Costs" value={n(data.costs_total)} />
            <Metric
              label="Timesheet cost"
              value={`${n(data.timesheet_amount)} (${Number(data.timesheet_hours)} h)`}
            />
            <Metric label="Total cost" value={n(data.total_cost)} />
            <Metric
              label="Unbilled"
              value={`${n(data.unbilled_amount)} (${Number(data.unbilled_hours || 0)} h)`}
            />
            <Metric label="Remaining" value={n(data.budget_remaining)} warn={remaining < 0} />
            <Metric label="Open tasks" value={String(data.open_tasks)} />
          </Box>
          {data.latest_invoice_id ? (
            <Button
              component={Link}
              href={`/sales/invoices/${data.latest_invoice_id}`}
              size="small"
              sx={{ alignSelf: "flex-start" }}
            >
              {data.latest_invoice_no || "AR invoice"}
            </Button>
          ) : null}
          {canBill ? (
            <Button variant="outlined" disabled={busy} onClick={() => void bill()} sx={{ alignSelf: "flex-start" }}>
              Create AR invoice
            </Button>
          ) : null}
          {!hasCustomer && unbilled > 0 ? (
            <Typography variant="body2" color="text.secondary">
              Set a customer before billing approved time.
            </Typography>
          ) : null}
        </Stack>
      )}
    </DetailSection>
  );
}
