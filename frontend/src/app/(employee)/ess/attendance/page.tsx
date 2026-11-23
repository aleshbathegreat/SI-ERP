"use client";

import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import EssSection, { EssPanel, EssStatusChip } from "@/components/ess/EssSection";
import {
  EssAttendance,
  essAttendanceException,
  essPunch,
  essRequestRegularization,
  fetchEssAttendance,
  fetchEssDashboard,
} from "@/lib/essApi";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { useSnackbar } from "notistack";

function clockOf(value?: string | null) {
  if (!value) return "—";
  const text = String(value);
  if (text.includes("T")) return text.slice(11, 16);
  return text.slice(0, 5);
}

export default function EssAttendancePage() {
  const { enqueueSnackbar } = useSnackbar();
  const [rows, setRows] = useState<EssAttendance[]>([]);
  const [free, setFree] = useState(false);
  const [today, setToday] = useState<EssAttendance | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [notes, setNotes] = useState("");
  const [fixDate, setFixDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [fixIn, setFixIn] = useState("");
  const [fixOut, setFixOut] = useState("");
  const [fixReason, setFixReason] = useState("");
  const [err, setErr] = useState("");
  const [month, setMonth] = useState(() => new Date().toISOString().slice(0, 7));

  const load = async () => {
    setLoading(true);
    setErr("");
    try {
      const [list, dash] = await Promise.all([
        fetchEssAttendance(month),
        fetchEssDashboard(),
      ]);
      setRows(list);
      setFree(Boolean(dash.today?.is_attendance_free));
      const att = dash.today?.attendance as EssAttendance | null;
      setToday(att);
    } catch (e: unknown) {
      setErr(getApiErrorMessage(e, "Could not load attendance"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [month]);

  const punch = async (kind: "check-in" | "check-out") => {
    setBusy(true);
    try {
      await essPunch(kind);
      enqueueSnackbar(kind === "check-in" ? "Checked in" : "Checked out", {
        variant: "success",
      });
      await load();
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Punch failed"), errorSnackbarOpts);
    } finally {
      setBusy(false);
    }
  };

  const requestFix = async () => {
    setBusy(true);
    try {
      await essRequestRegularization({
        work_date: fixDate,
        check_in: fixIn || undefined,
        check_out: fixOut || undefined,
        reason: fixReason,
      });
      enqueueSnackbar("Correction sent to HR", { variant: "success" });
      setFixReason("");
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Could not send the correction"), errorSnackbarOpts);
    } finally {
      setBusy(false);
    }
  };

  const logException = async () => {
    setBusy(true);
    try {
      await essAttendanceException(notes || "ESS attendance exception");
      enqueueSnackbar("Exception logged for review", { variant: "success" });
      setNotes("");
      await load();
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Could not log exception"), errorSnackbarOpts);
    } finally {
      setBusy(false);
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
      title="Attendance"
      subtitle="Check in and out, or flag a day for HR review."
    >
      {err ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {err}
        </Alert>
      ) : null}

      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems={{ sm: "center" }} sx={{ mb: 2 }}>
        <TextField
          type="month"
          label="Month"
          size="small"
          value={month}
          onChange={(e) => setMonth(e.target.value)}
          slotProps={{ inputLabel: { shrink: true } }}
        />
      </Stack>
      <Box
        sx={{
          display: "grid",
          gap: 2,
          gridTemplateColumns: { xs: "1fr 1fr", md: "repeat(4, 1fr)" },
          mb: 2,
        }}
      >
        {[
          ["Present", rows.filter((r) => ["present", "late", "wfh", "regularized", "half_day", "early_leave", "exempt"].includes(r.status)).length],
          ["Late", rows.filter((r) => r.status === "late" || (r.late_minutes || 0) > 0).length],
          ["Half days", rows.filter((r) => r.is_half_day || r.status === "half_day").length],
          ["Hours", (rows.reduce((sum, r) => sum + (r.worked_minutes || 0), 0) / 60).toFixed(1)],
        ].map(([label, value]) => (
          <EssPanel key={String(label)}>
            <Typography variant="overline" color="text.secondary">{label}</Typography>
            <Typography variant="h5">{value}</Typography>
          </EssPanel>
        ))}
      </Box>

      <Box
        sx={{
          display: "grid",
          gap: 2,
          gridTemplateColumns: { xs: "1fr", md: "0.9fr 1.1fr" },
        }}
      >
        <Stack spacing={2}>
          <EssPanel>
            <Typography fontWeight={700} sx={{ mb: 1 }}>
              Today
            </Typography>
            {free ? (
              <Alert severity="info">
                You are attendance-exempt. No punch required.
              </Alert>
            ) : (
              <Stack spacing={1.5}>
                <Typography variant="body2">
                  Status:{" "}
                  {today?.status ? (
                    <EssStatusChip status={today.status} />
                  ) : (
                    "Not recorded"
                  )}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  In {clockOf(today?.check_in)} · Out {clockOf(today?.check_out)}
                </Typography>
                <Stack direction="row" spacing={1}>
                  <Button
                    variant="contained"
                    disabled={busy || Boolean(today?.check_in)}
                    onClick={() => punch("check-in")}
                  >
                    Check in
                  </Button>
                  <Button
                    variant="outlined"
                    disabled={busy || !today?.check_in || Boolean(today?.check_out)}
                    onClick={() => punch("check-out")}
                  >
                    Check out
                  </Button>
                </Stack>
              </Stack>
            )}
          </EssPanel>

          {!free ? (
            <EssPanel>
              <Typography fontWeight={700} sx={{ mb: 1 }}>
                Correct a day
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                Ask HR to set the punches. The day changes only after approval.
              </Typography>
              <Stack spacing={1.5}>
                <TextField
                  type="date"
                  label="Date"
                  value={fixDate}
                  onChange={(e) => setFixDate(e.target.value)}
                  slotProps={{ inputLabel: { shrink: true } }}
                />
                <Stack direction="row" spacing={1}>
                  <TextField
                    type="time"
                    label="In"
                    value={fixIn}
                    onChange={(e) => setFixIn(e.target.value)}
                    slotProps={{ inputLabel: { shrink: true } }}
                    fullWidth
                  />
                  <TextField
                    type="time"
                    label="Out"
                    value={fixOut}
                    onChange={(e) => setFixOut(e.target.value)}
                    slotProps={{ inputLabel: { shrink: true } }}
                    fullWidth
                  />
                </Stack>
                <TextField
                  label="Reason"
                  required
                  value={fixReason}
                  onChange={(e) => setFixReason(e.target.value)}
                />
                <Button variant="contained" disabled={busy || !fixReason.trim()} onClick={requestFix}>
                  Send to HR
                </Button>
              </Stack>
            </EssPanel>
          ) : null}

          {!free ? (
            <EssPanel>
              <Typography fontWeight={700} sx={{ mb: 1 }}>
                Report an exception
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                Missed punch, site visit, or other note for HR.
              </Typography>
              <TextField
                fullWidth
                multiline
                minRows={2}
                label="Notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                sx={{ mb: 1.5 }}
              />
              <Button variant="outlined" disabled={busy} onClick={logException}>
                Submit exception
              </Button>
            </EssPanel>
          ) : null}
        </Stack>

        <EssPanel>
          <Typography fontWeight={700} sx={{ mb: 1.5 }}>
            Monthly timesheet
          </Typography>
          {rows.length === 0 ? (
            <Typography color="text.secondary" variant="body2">
              No attendance records for this month.
            </Typography>
          ) : (
            <Box sx={{ overflowX: "auto" }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Date</TableCell>
                    <TableCell>In</TableCell>
                    <TableCell>Out</TableCell>
                    <TableCell>Hours</TableCell>
                    <TableCell>Late</TableCell>
                    <TableCell>Status</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {rows.map((r) => (
                    <TableRow key={r.id} hover>
                      <TableCell>
                        {r.work_date}
                        <Button
                          size="small"
                          sx={{ ml: 0.5, minWidth: 0 }}
                          onClick={() => setFixDate(r.work_date)}
                        >
                          Correct
                        </Button>
                      </TableCell>
                      <TableCell>{clockOf(r.check_in)}</TableCell>
                      <TableCell>{clockOf(r.check_out)}</TableCell>
                      <TableCell>{r.worked_hours ?? "—"}</TableCell>
                      <TableCell>{r.late_minutes || 0}</TableCell>
                      <TableCell><EssStatusChip status={r.status} /></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          )}
        </EssPanel>
      </Box>
    </EssSection>
  );
}
