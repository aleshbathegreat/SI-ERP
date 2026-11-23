"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  LinearProgress,
  Stack,
  Typography,
} from "@mui/material";
import { alpha } from "@mui/material/styles";
import EventAvailableOutlinedIcon from "@mui/icons-material/EventAvailableOutlined";
import FingerprintOutlinedIcon from "@mui/icons-material/FingerprintOutlined";
import PaymentsOutlinedIcon from "@mui/icons-material/PaymentsOutlined";
import FolderOutlinedIcon from "@mui/icons-material/FolderOutlined";
import ReceiptLongOutlinedIcon from "@mui/icons-material/ReceiptLongOutlined";
import CalendarMonthOutlinedIcon from "@mui/icons-material/CalendarMonthOutlined";
import AccountBalanceWalletOutlinedIcon from "@mui/icons-material/AccountBalanceWalletOutlined";

function TintIcon({
  tone,
  children,
}: {
  tone: "primary" | "success" | "info" | "warning";
  children: ReactNode;
}) {
  return (
    <Box
      sx={{
        width: 40,
        height: 40,
        borderRadius: 2,
        display: "grid",
        placeItems: "center",
        flexShrink: 0,
        color: `${tone}.main`,
        bgcolor: (t) => alpha(t.palette[tone].main, 0.14),
      }}
    >
      {children}
    </Box>
  );
}
import EssSection, { EssPanel, EssStatusChip } from "@/components/ess/EssSection";
import {
  EssDashboard,
  fetchEssDashboard,
  essPunch,
} from "@/lib/essApi";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { useSnackbar } from "notistack";

const QUICK = [
  {
    href: "/ess/leave",
    label: "Request leave",
    hint: "Annual, sick, and more",
    icon: <EventAvailableOutlinedIcon />,
  },
  {
    href: "/ess/attendance",
    label: "Attendance",
    hint: "Check in or review days",
    icon: <FingerprintOutlinedIcon />,
  },
  {
    href: "/ess/payslips",
    label: "Payslips",
    hint: "View and print PDF",
    icon: <PaymentsOutlinedIcon />,
  },
  {
    href: "/ess/documents",
    label: "Documents",
    hint: "Contracts and letters",
    icon: <FolderOutlinedIcon />,
  },
  {
    href: "/ess/claims",
    label: "Claims",
    hint: "Expense reimbursements",
    icon: <ReceiptLongOutlinedIcon />,
  },
];

export default function EssHomePage() {
  const { enqueueSnackbar } = useSnackbar();
  const [data, setData] = useState<EssDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [punching, setPunching] = useState(false);
  const [showPay, setShowPay] = useState(false);
  const [clock, setClock] = useState("");

  const load = async () => {
    setLoading(true);
    setErr("");
    try {
      setData(await fetchEssDashboard());
    } catch (e: unknown) {
      setErr(getApiErrorMessage(e, "Could not load your workplace"));
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    const tick = () =>
      setClock(
        new Date().toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" }),
      );
    tick();
    const id = window.setInterval(tick, 30000);
    return () => window.clearInterval(id);
  }, []);

  const emp = data?.employee;
  const name =
    emp?.full_name ||
    [emp?.first_name, emp?.last_name].filter(Boolean).join(" ") ||
    "there";
  const todayAtt = data?.today?.attendance as
    | { status?: string; check_in?: string | null; check_out?: string | null }
    | null
    | undefined;
  const free = data?.today?.is_attendance_free;
  const shift = data?.workplace?.shift;
  const shiftLine = shift ? `Shift ${shift.name} (${shift.start}–${shift.end})` : "";
  const monthName = data?.today?.work_date
    ? new Date(`${data.today.work_date}T12:00:00`).toLocaleString(undefined, { month: "long" })
    : "This month";
  const latest = data?.recent_payslips?.[0];
  const showLoan = (data?.loan?.count ?? 0) > 0;
  const identity = [
    data?.workplace?.designation,
    emp?.employee_code,
    data?.workplace?.department,
    data?.workplace?.location,
    shiftLine,
  ].filter(Boolean) as string[];
  const payLine = (amount: string | number, currency?: string) =>
    showPay
      ? `${Number(amount).toLocaleString()} ${currency || "PKR"}`
      : `${currency || "PKR"} ••••••`;

  const doPunch = async (kind: "check-in" | "check-out") => {
    setPunching(true);
    try {
      await essPunch(kind);
      enqueueSnackbar(kind === "check-in" ? "Checked in" : "Checked out", {
        variant: "success",
      });
      await load();
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Punch failed"), errorSnackbarOpts);
    } finally {
      setPunching(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: "grid", placeItems: "center", minHeight: 280 }}>
        <CircularProgress size={32} />
      </Box>
    );
  }

  if (err && !data) {
    return (
      <Alert severity="error" action={<Button onClick={load}>Retry</Button>}>
        {err}
      </Alert>
    );
  }

  return (
    <EssSection
      title={`Good day, ${name.split(" ")[0]}`}
      subtitle="Your leave, attendance, payslips, and documents — in one place."
    >
      {err ? (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {err}
        </Alert>
      ) : null}

      {identity.length > 0 || (data?.counts.pending_leaves ?? 0) > 0 ? (
        <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mb: 2.5 }}>
          {identity.map((label) => (
            <Chip key={label} label={label} size="small" variant="outlined" />
          ))}
          {(data?.counts.pending_leaves ?? 0) > 0 ? (
            <Chip
              color="warning"
              size="small"
              label={`${data?.counts.pending_leaves} pending leave`}
            />
          ) : null}
        </Stack>
      ) : null}

      <Box sx={{ mb: 3 }}>
        <EssPanel>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            spacing={2}
            justifyContent="space-between"
            alignItems={{ xs: "flex-start", sm: "center" }}
          >
            <Box>
              <Typography variant="overline" color="text.secondary" sx={{ letterSpacing: "0.14em" }}>
                Attendance punch
              </Typography>
              <Typography
                sx={{
                  fontFamily: '"Fraunces", Georgia, serif',
                  fontWeight: 700,
                  fontSize: { xs: "2rem", md: "2.4rem" },
                  letterSpacing: "-0.03em",
                  lineHeight: 1.1,
                  mt: 0.5,
                }}
              >
                {clock || "—"}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                {data?.today?.work_date}
                {free ? " · Attendance exempt" : ""}
              </Typography>
            </Box>
            <Stack spacing={1} alignItems={{ xs: "flex-start", sm: "flex-end" }}>
              {todayAtt?.status ? (
                <EssStatusChip status={String(todayAtt.status)} />
              ) : (
                <Typography variant="body2" color="text.secondary">
                  {free ? "No check-in required" : "Not punched yet"}
                </Typography>
              )}
              <Typography variant="body2" color="text.secondary">
                In {todayAtt?.check_in ? String(todayAtt.check_in).slice(11, 16) : "—"} · Out{" "}
                {todayAtt?.check_out ? String(todayAtt.check_out).slice(11, 16) : "—"}
              </Typography>
              {free ? null : (
                <Stack direction="row" spacing={1}>
                  <Button
                    variant="contained"
                    disabled={punching || Boolean(todayAtt?.check_in)}
                    onClick={() => doPunch("check-in")}
                  >
                    Check in
                  </Button>
                  <Button
                    variant="outlined"
                    disabled={punching || !todayAtt?.check_in || Boolean(todayAtt?.check_out)}
                    onClick={() => doPunch("check-out")}
                  >
                    Check out
                  </Button>
                </Stack>
              )}
            </Stack>
          </Stack>
        </EssPanel>
      </Box>

      <Box
        sx={{
          display: "grid",
          gap: 2,
          gridTemplateColumns: {
            xs: "1fr",
            sm: "1fr 1fr",
            lg: showLoan ? "1fr 1fr 1fr 1fr" : "1fr 1fr 1fr",
          },
          mb: 3,
        }}
      >
        <EssPanel>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <TintIcon tone="success">
              <CalendarMonthOutlinedIcon fontSize="small" />
            </TintIcon>
            <Box>
              <Typography variant="overline" color="text.secondary">
                Attendance ({monthName})
              </Typography>
              <Typography variant="h5">
                {data?.month_attendance?.present ?? 0} days present
              </Typography>
            </Box>
          </Stack>
          <Typography variant="body2" sx={{ mt: 1.25 }}>
            <Box component="span" sx={{ color: "success.main" }}>
              {data?.month_attendance?.on_time ?? 0} on time
            </Box>
            {" · "}
            <Box component="span" sx={{ color: "warning.main" }}>
              {data?.month_attendance?.late ?? 0} late
            </Box>
            {" · "}
            <Box component="span" sx={{ color: "error.main" }}>
              {data?.month_attendance?.absent ?? 0} absent
            </Box>
          </Typography>
        </EssPanel>
        <EssPanel>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <TintIcon tone="info">
              <EventAvailableOutlinedIcon fontSize="small" />
            </TintIcon>
            <Box>
              <Typography variant="overline" color="text.secondary">
                Leave balance ({data?.leave_summary?.year || ""})
              </Typography>
              <Typography variant="h5">
                {Number(data?.leave_summary?.remaining || 0).toLocaleString()} days left
              </Typography>
            </Box>
          </Stack>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1.25 }}>
            {Number(data?.leave_summary?.used || 0).toLocaleString()} availed of{" "}
            {Number(data?.leave_summary?.quota || 0).toLocaleString()} quota
          </Typography>
        </EssPanel>
        <EssPanel>
          <Stack direction="row" spacing={1.5} alignItems="center" justifyContent="space-between">
            <Stack direction="row" spacing={1.5} alignItems="center">
              <TintIcon tone="primary">
                <PaymentsOutlinedIcon fontSize="small" />
              </TintIcon>
              <Typography variant="overline" color="text.secondary">
                Latest net salary
              </Typography>
            </Stack>
            <Button size="small" onClick={() => setShowPay((v) => !v)}>
              {showPay ? "Hide" : "Show"}
            </Button>
          </Stack>
          <Typography variant="h5" sx={{ mt: 1.25 }}>
            {latest ? payLine(latest.net_pay, latest.currency) : "No payslip yet"}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {latest?.period_name || "When payroll is paid, it appears here."}
          </Typography>
        </EssPanel>
        {showLoan ? (
          <EssPanel>
            <Stack direction="row" spacing={1.5} alignItems="center">
              <TintIcon tone="warning">
                <AccountBalanceWalletOutlinedIcon fontSize="small" />
              </TintIcon>
              <Box>
                <Typography variant="overline" color="text.secondary">
                  Active loan balance
                </Typography>
                <Typography variant="h5">
                  {Number(data?.loan?.outstanding || 0).toLocaleString()} PKR
                </Typography>
              </Box>
            </Stack>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1.25 }}>
              {Number(data?.loan?.installment || 0).toLocaleString()} PKR / month
            </Typography>
          </EssPanel>
        ) : null}
      </Box>

      <Box
        sx={{
          display: "grid",
          gap: 1.5,
          gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "repeat(5, 1fr)" },
          mb: 3,
        }}
      >
        {QUICK.map((q) => (
          <Box
            key={q.href}
            component={Link}
            href={q.href}
            sx={{
              display: "flex",
              gap: 1.5,
              alignItems: "center",
              p: 2,
              borderRadius: 2,
              textDecoration: "none",
              color: "inherit",
              border: "1px solid",
              borderColor: "divider",
              bgcolor: (t) =>
                t.palette.mode === "dark"
                  ? "rgba(255,255,255,0.03)"
                  : "rgba(255,255,255,0.65)",
              transition: "transform 180ms ease, border-color 180ms ease",
              "&:hover": {
                transform: "translateY(-2px)",
                borderColor: "primary.main",
              },
            }}
          >
            <Box sx={{ color: "primary.main", display: "grid", placeItems: "center" }}>
              {q.icon}
            </Box>
            <Box>
              <Typography fontWeight={700}>{q.label}</Typography>
              <Typography variant="body2" color="text.secondary">
                {q.hint}
              </Typography>
            </Box>
          </Box>
        ))}
      </Box>

      {(data?.leave_summary?.balances || []).length > 0 ? (
        <Box sx={{ mb: 3 }}>
        <EssPanel>
          <Typography fontWeight={700} sx={{ mb: 1.5 }}>
            Leave entitlements
          </Typography>
          <Stack spacing={1.5}>
            {data?.leave_summary?.balances.map((row) => {
              const quota = Number(row.quota) || 0;
              const remaining = Number(row.remaining) || 0;
              const pct = quota > 0 ? Math.min(100, Math.round((remaining / quota) * 100)) : 0;
              return (
                <Box key={row.name}>
                  <Stack direction="row" justifyContent="space-between">
                    <Typography variant="body2" fontWeight={600}>{row.name}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {remaining.toLocaleString()} remaining / {quota.toLocaleString()} quota
                    </Typography>
                  </Stack>
                  <LinearProgress variant="determinate" value={pct} sx={{ mt: 0.5, borderRadius: 1 }} />
                </Box>
              );
            })}
          </Stack>
        </EssPanel>
        </Box>
      ) : null}

      <Box
        sx={{
          display: "grid",
          gap: 2,
          gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
          mb: 3,
        }}
      >
        <EssPanel>
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
            <Typography fontWeight={700}>My tasks</Typography>
            <Button component={Link} href="/ess/tasks" size="small">Board</Button>
          </Stack>
          {(data?.tasks || []).length === 0 ? (
            <Typography color="text.secondary" variant="body2">No pending tasks assigned.</Typography>
          ) : (
            (data?.tasks || []).map((task) => (
              <Typography key={task.id} variant="body2" sx={{ py: 0.5 }}>{task.title}</Typography>
            ))
          )}
        </EssPanel>
        <EssPanel>
          <Typography fontWeight={700} sx={{ mb: 1.5 }}>Upcoming holidays</Typography>
          {(data?.holidays || []).length === 0 ? (
            <Typography color="text.secondary" variant="body2">No upcoming holidays scheduled.</Typography>
          ) : (
            (data?.holidays || []).map((row) => (
              <Typography key={row.date + row.name} variant="body2" sx={{ py: 0.5 }}>
                {row.date} · {row.name}
              </Typography>
            ))
          )}
        </EssPanel>
        <EssPanel>
          <Typography fontWeight={700} sx={{ mb: 1.5 }}>Birthdays this month</Typography>
          {(data?.birthdays || []).length === 0 ? (
            <Typography color="text.secondary" variant="body2">No colleague birthdays this month.</Typography>
          ) : (
            (data?.birthdays || []).map((row) => (
              <Typography key={row.name + row.day} variant="body2" sx={{ py: 0.5 }}>
                {row.name}{row.department ? ` · ${row.department}` : ""} · day {row.day}
              </Typography>
            ))
          )}
        </EssPanel>
      </Box>

      <Box
        sx={{
          display: "grid",
          gap: 2,
          gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
        }}
      >
        <EssPanel>
          <Typography fontWeight={700} sx={{ mb: 1.5 }}>
            Recent leave
          </Typography>
          {(data?.recent_leaves || []).length === 0 ? (
            <Typography color="text.secondary" variant="body2">
              No leave yet.{" "}
              <Link href="/ess/leave">Request leave</Link>
            </Typography>
          ) : (
            (data?.recent_leaves || []).map((l) => (
              <Box
                key={l.id}
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 1,
                  py: 0.75,
                  borderBottom: "1px solid",
                  borderColor: "divider",
                }}
              >
                <Typography variant="body2">
                  {l.leave_type_name || "Leave"} · {l.start_date} → {l.end_date}
                </Typography>
                <EssStatusChip status={l.status} />
              </Box>
            ))
          )}
        </EssPanel>
        <EssPanel>
          <Typography fontWeight={700} sx={{ mb: 1.5 }}>
            Recent payslips
          </Typography>
          {(data?.recent_payslips || []).length === 0 ? (
            <Typography color="text.secondary" variant="body2">
              No payslips yet.
            </Typography>
          ) : (
            (data?.recent_payslips || []).map((p) => (
              <Box
                key={p.id}
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 1,
                  py: 0.75,
                  borderBottom: "1px solid",
                  borderColor: "divider",
                }}
              >
                <Typography variant="body2">
                  {p.period_name || `Period #${p.period}`}
                </Typography>
                <Typography variant="body2" fontWeight={600}>
                  {payLine(p.net_pay, p.currency)}
                </Typography>
              </Box>
            ))
          )}
          <Button component={Link} href="/ess/payslips" size="small" sx={{ mt: 1.5 }}>
            All payslips
          </Button>
        </EssPanel>
      </Box>
    </EssSection>
  );
}
