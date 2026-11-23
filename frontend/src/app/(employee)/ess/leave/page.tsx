"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import DateTextField, { endBeforeStart, todayISO } from "@/components/DateTextField";
import RelationSelect, { RELATIONS } from "@/components/crud/RelationSelect";
import EssSection, { EssPanel, EssStatusChip } from "@/components/ess/EssSection";
import { usePermissions } from "@/hooks/usePermissions";
import {
  EssLeave,
  EssLeaveBalance,
  fetchEssLeaveBalances,
  fetchEssLeaveTypes,
  fetchEssLeaves,
  submitEssLeave,
} from "@/lib/essApi";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { useSnackbar } from "notistack";

function inclusiveDays(start: string, end: string): string {
  if (!start || !end) return "";
  const a = new Date(`${start}T00:00:00`);
  const b = new Date(`${end}T00:00:00`);
  if (Number.isNaN(a.getTime()) || Number.isNaN(b.getTime()) || b < a) return "";
  return String(Math.floor((b.getTime() - a.getTime()) / 86400000) + 1);
}

function blankLeaveForm() {
  const today = todayISO();
  return { leave_type: "", start_date: today, end_date: today, reason: "" };
}

export default function EssLeavePage() {
  const { enqueueSnackbar } = useSnackbar();
  const { canAdd, canView, isOwner } = usePermissions();
  const canManageTypes = isOwner || canView("hr.leave_types");
  const [types, setTypes] = useState<{ id: number; name: string; code: string }[]>([]);
  const [leaves, setLeaves] = useState<EssLeave[]>([]);
  const [balances, setBalances] = useState<EssLeaveBalance[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");
  const [form, setForm] = useState(blankLeaveForm);

  const days = useMemo(
    () => inclusiveDays(form.start_date, form.end_date),
    [form.start_date, form.end_date]
  );

  const load = async () => {
    setLoading(true);
    setErr("");
    const [t, l, b] = await Promise.allSettled([
      fetchEssLeaveTypes(),
      fetchEssLeaves(),
      fetchEssLeaveBalances(),
    ]);
    if (l.status === "fulfilled") setLeaves(l.value);
    if (b.status === "fulfilled") setBalances(b.value);
    const catalog = t.status === "fulfilled" && Array.isArray(t.value) ? t.value : [];
    const fromBalances =
      b.status === "fulfilled"
        ? b.value
            .filter((row) => row.leave_type)
            .map((row) => ({
              id: Number(row.leave_type),
              name: row.leave_type_name || row.leave_type_code || "Leave",
              code: row.leave_type_code || "",
            }))
        : [];
    const merged = new Map<number, { id: number; name: string; code: string }>();
    for (const row of [...catalog, ...fromBalances]) {
      if (row?.id) merged.set(Number(row.id), { id: Number(row.id), name: row.name, code: row.code });
    }
    setTypes(Array.from(merged.values()));
    if (t.status === "rejected" && merged.size === 0) {
      setErr(getApiErrorMessage(t.reason, "Could not load leave types"));
    }
    setLoading(false);
  };

  useEffect(() => {
    load();
  }, []);

  const submit = async () => {
    if (endBeforeStart(form.start_date, form.end_date)) {
      enqueueSnackbar("End date cannot be before the start date.", { variant: "warning" });
      return;
    }
    setSaving(true);
    try {
      await submitEssLeave({
        leave_type: Number(form.leave_type),
        start_date: form.start_date,
        end_date: form.end_date,
        days,
        reason: form.reason,
        status: "pending",
      });
      enqueueSnackbar("Leave submitted for approval", { variant: "success" });
      setForm(blankLeaveForm());
      await load();
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Could not submit leave"), errorSnackbarOpts);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: "grid", placeItems: "center", minHeight: 240 }}>
        <CircularProgress size={32} />
      </Box>
    );
  }

  return (
    <EssSection
      title="Leave"
      subtitle="Request time off and track approval status."
    >
      {err ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {err}
        </Alert>
      ) : null}

      <Box
        sx={{
          display: "grid",
          gap: 2,
          gridTemplateColumns: { xs: "1fr", md: "1fr 1.1fr" },
        }}
      >
        <EssPanel>
          <Typography fontWeight={700} sx={{ mb: 1.5 }}>
            New request
          </Typography>
          <Stack spacing={1.5}>
            {canManageTypes ? (
              <RelationSelect
                label="Leave type"
                required
                value={form.leave_type}
                relation={
                  isOwner || canAdd("hr.leave_types")
                    ? RELATIONS.leaveType
                    : { ...RELATIONS.leaveType, createFields: [] }
                }
                onChange={(v) => setForm({ ...form, leave_type: v })}
              />
            ) : (
              <TextField
                select
                label="Leave type"
                value={form.leave_type}
                helperText={
                  types.length
                    ? undefined
                    : "No leave types yet. An admin adds them under HR · Leave types."
                }
                onChange={(e) => setForm({ ...form, leave_type: e.target.value })}
              >
                <MenuItem value="" disabled>
                  {types.length ? "Select leave type" : "No leave types"}
                </MenuItem>
                {types.map((t) => (
                  <MenuItem key={t.id} value={String(t.id)}>
                    {t.name || t.code}
                  </MenuItem>
                ))}
              </TextField>
            )}
            <DateTextField
              label="Start date"
              value={form.start_date}
              showFormatHint={false}
              onChange={(e) => setForm({ ...form, start_date: e.target.value })}
            />
            <DateTextField
              label="End date"
              value={form.end_date}
              showFormatHint={false}
              notBefore={form.start_date}
              onChange={(e) => setForm({ ...form, end_date: e.target.value })}
            />
            <TextField
              label="Days (estimate)"
              value={days || "—"}
              InputProps={{ readOnly: true }}
              helperText="Server applies working-day rules on submit"
            />
            <TextField
              label="Reason"
              multiline
              minRows={2}
              value={form.reason}
              onChange={(e) => setForm({ ...form, reason: e.target.value })}
            />
            <Button
              variant="contained"
              disabled={saving || !form.leave_type || !days}
              onClick={submit}
            >
              Submit leave
            </Button>
          </Stack>
        </EssPanel>

        <EssPanel>
          <Typography fontWeight={700} sx={{ mb: 1.5 }}>
            My balances
          </Typography>
          {balances.length === 0 ? (
            <Typography color="text.secondary" variant="body2" sx={{ mb: 2 }}>
              No balances yet — HR will accrue quotas.
            </Typography>
          ) : (
            balances.map((b) => (
              <Box
                key={b.id}
                sx={{
                  py: 1,
                  borderBottom: "1px solid",
                  borderColor: "divider",
                  display: "flex",
                  justifyContent: "space-between",
                }}
              >
                <Typography variant="body2">
                  {b.leave_type_name || b.leave_type_code || "Leave"}
                </Typography>
                <Typography fontWeight={600}>{b.available} avail</Typography>
              </Box>
            ))
          )}
          <Typography fontWeight={700} sx={{ mb: 1.5, mt: 2 }}>
            My requests
          </Typography>
          {leaves.length === 0 ? (
            <Typography color="text.secondary" variant="body2">
              No leave requests yet.
            </Typography>
          ) : (
            leaves.map((l) => (
              <Box
                key={l.id}
                sx={{
                  py: 1.25,
                  borderBottom: "1px solid",
                  borderColor: "divider",
                }}
              >
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    gap: 1,
                    mb: 0.5,
                  }}
                >
                  <Typography fontWeight={600}>
                    {l.leave_type_name || "Leave"}
                  </Typography>
                  <EssStatusChip status={l.status} />
                </Box>
                <Typography variant="body2" color="text.secondary">
                  {l.start_date} → {l.end_date} · {l.days} day(s)
                </Typography>
                {l.reason ? (
                  <Typography variant="body2" sx={{ mt: 0.5 }}>
                    {l.reason}
                  </Typography>
                ) : null}
              </Box>
            ))
          )}
        </EssPanel>
      </Box>
    </EssSection>
  );
}
