"use client";

import { useEffect, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Box,
  Button,
  Card,
  CardContent,
  LinearProgress,
  Skeleton,
  Stack,
  Typography,
} from "@mui/material";
import PeopleAltIcon from "@mui/icons-material/PeopleAlt";
import AccountTreeIcon from "@mui/icons-material/AccountTree";
import StorefrontIcon from "@mui/icons-material/Storefront";
import EventBusyIcon from "@mui/icons-material/EventBusy";
import PaymentsIcon from "@mui/icons-material/Payments";
import ModuleGate from "@/components/ModuleGate";
import PageHeader from "@/components/PageHeader";
import {
  BarChart,
  DonutChart,
  DualLineChart,
  LegendList,
  MeterRing,
} from "@/components/dashboard/Charts";
import { usePermissions } from "@/hooks/usePermissions";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { fetchDashboardRequest } from "@/store/dashboard/slice";

const cards = [
  {
    key: "employees" as const,
    label: "Employees",
    icon: <PeopleAltIcon fontSize="small" color="primary" />,
    module: "hr.employees",
    href: "/hr/employees",
  },
  {
    key: "accounts" as const,
    label: "GL accounts",
    icon: <AccountTreeIcon fontSize="small" color="primary" />,
    module: "finance.accounts",
    href: "/finance/accounts",
  },
  {
    key: "vendors" as const,
    label: "Vendors",
    icon: <StorefrontIcon fontSize="small" color="primary" />,
    module: "finance.vendors",
    href: "/finance/vendors",
  },
  {
    key: "pending_leaves" as const,
    label: "Pending leave",
    icon: <EventBusyIcon fontSize="small" color="warning" />,
    module: "hr.leaves",
    href: "/hr/leaves",
  },
  {
    key: "open_payroll_periods" as const,
    label: "Open payroll",
    icon: <PaymentsIcon fontSize="small" color="secondary" />,
    module: "payroll.periods",
    href: "/payroll",
  },
];

const roleShortcuts: Record<string, { label: string; href: string; module: string }[]> = {
  finance: [
    { label: "Budgets", href: "/finance/budgets", module: "finance.budgets" },
    { label: "AP invoices", href: "/finance/invoices", module: "finance.invoices" },
    { label: "Banks", href: "/finance/banks", module: "finance.banks" },
    { label: "Assets", href: "/finance/assets", module: "finance.assets" },
    { label: "Reports", href: "/finance/reports", module: "finance.reports" },
  ],
  hr: [
    { label: "Recruitment", href: "/hr/recruitment", module: "hr.recruitment" },
    { label: "Attendance", href: "/hr/attendance", module: "hr.attendance" },
    { label: "Leave", href: "/hr/leaves", module: "hr.leaves" },
    { label: "Performance", href: "/hr/performance", module: "hr.performance" },
  ],
  payroll: [
    { label: "Structures", href: "/payroll/structures", module: "payroll.structures" },
    { label: "Payroll runs", href: "/payroll", module: "payroll.periods" },
  ],
  initiator: [
    { label: "Journal entries", href: "/finance/journals", module: "finance.journals" },
    { label: "Invoices", href: "/finance/invoices", module: "finance.invoices" },
    { label: "Leave", href: "/hr/leaves", module: "hr.leaves" },
  ],
  employee: [{ label: "ESS", href: "/ess", module: "ess" }],
  approver: [
    { label: "Approvals", href: "/approvals", module: "approvals" },
    { label: "Journal entries", href: "/finance/journals", module: "finance.journals" },
    { label: "Leave", href: "/hr/leaves", module: "hr.leaves" },
    { label: "Payroll", href: "/payroll", module: "payroll.periods" },
  ],
  admin: [
    { label: "Roles", href: "/settings/roles", module: "settings.roles" },
    { label: "Users", href: "/settings/users", module: "settings.users" },
    { label: "Audit", href: "/settings/audit", module: "settings.audit" },
  ],
  owner: [
    { label: "Roles", href: "/settings/roles", module: "settings.roles" },
    { label: "Billing", href: "/billing", module: "billing" },
    { label: "Users", href: "/settings/users", module: "settings.users" },
  ],
  viewer: [
    { label: "Reports", href: "/finance/reports", module: "finance.reports" },
    { label: "Audit", href: "/settings/audit", module: "settings.audit" },
  ],
};

const STATUS_COLORS: Record<string, string> = {
  pending: "#D4A017",
  approved: "#4CAF7A",
  rejected: "#F04438",
  cancelled: "#9AA8B6",
  draft: "#9AA8B6",
  submitted: "#E08A5A",
  posted: "#4BA3C7",
  paid: "#4CAF7A",
  open: "#4BA3C7",
  processing: "#E08A5A",
  closed: "#7B8CDE",
};

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <Typography
      variant="subtitle2"
      color="text.secondary"
      sx={{
        mb: 1.5,
        textTransform: "uppercase",
        letterSpacing: "0.06em",
        fontWeight: 600,
      }}
    >
      {children}
    </Typography>
  );
}

export default function DashboardPage() {
  const dispatch = useAppDispatch();
  const router = useRouter();
  const { stats, loading } = useAppSelector((s) => s.dashboard);
  const user = useAppSelector((s) => s.auth.user);
  const organization = useAppSelector((s) => s.auth.organization);
  const { canView, isOwner } = usePermissions();
  const roleCode = user?.profile?.role || (isOwner ? "owner" : "employee");
  const isPlatformOwner = !!user?.is_superuser;

  useEffect(() => {
    if (isPlatformOwner && !organization) {
      router.replace("/platform");
    }
  }, [isPlatformOwner, organization, router]);

  useEffect(() => {
    if (isPlatformOwner && !organization) return;
    dispatch(fetchDashboardRequest());
  }, [dispatch, isPlatformOwner, organization]);

  const visibleCards = useMemo(
    () => cards.filter((c) => canView(c.module)),
    [canView]
  );

  const shortcuts = useMemo(() => {
    const list = roleShortcuts[roleCode] || roleShortcuts.owner;
    return list.filter((s) => canView(s.module));
  }, [roleCode, canView]);

  const leaveSeg = useMemo(
    () =>
      (stats?.leave_status || []).map((s) => ({
        label: s.status,
        value: s.count,
        color: STATUS_COLORS[s.status] || "#4BA3C7",
      })),
    [stats]
  );

  const journalSeg = useMemo(
    () =>
      (stats?.journal_status || []).map((s) => ({
        label: s.status,
        value: s.count,
        color: STATUS_COLORS[s.status] || "#4BA3C7",
      })),
    [stats]
  );

  const apSeg = useMemo(
    () =>
      (stats?.ap_status || []).map((s) => ({
        label: s.status,
        value: s.count,
        color: STATUS_COLORS[s.status] || "#E08A5A",
      })),
    [stats]
  );

  const attendanceBars = useMemo(() => {
    const a = stats?.attendance_month;
    if (!a) return [];
    return [
      { label: "Present", value: a.present },
      { label: "Late", value: a.late },
      { label: "Absent", value: a.absent },
      { label: "Other", value: a.other },
    ];
  }, [stats]);

  const health = stats?.health_score ?? 100;
  const healthLabel =
    health >= 80 ? "Healthy" : health >= 55 ? "Watch" : "Action needed";

  if (isPlatformOwner && !organization) {
    return null;
  }

  return (
    <ModuleGate module="dashboard">
      <PageHeader
        title="Dashboard"
        actions={
          isPlatformOwner ? (
            <Button component={Link} href="/platform" size="small" variant="outlined">
              Platform
            </Button>
          ) : undefined
        }
      />

      <Box
        sx={{
          display: "grid",
          gap: 2.5,
          gridTemplateColumns: { xs: "1fr", lg: "160px 1fr" },
          mb: 3,
          alignItems: "stretch",
        }}
      >
        <Card sx={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
          <CardContent sx={{ py: 2, width: "100%" }}>
            {loading && !stats ? (
              <Skeleton variant="circular" width={112} height={112} sx={{ mx: "auto" }} />
            ) : (
              <MeterRing value={health} label={healthLabel} size={128} />
            )}
          </CardContent>
        </Card>

        <Stack spacing={2}>
          {shortcuts.length > 0 ? (
            <Box>
              <SectionTitle>Shortcuts</SectionTitle>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {shortcuts.map((s) => (
                  <Button
                    key={s.href}
                    component={Link}
                    href={s.href}
                    target={s.href === "/ess" || s.href === "/guide" ? "_blank" : undefined}
                    rel={
                      s.href === "/ess" || s.href === "/guide"
                        ? "noopener noreferrer"
                        : undefined
                    }
                    variant="outlined"
                    size="small"
                    color="inherit"
                    sx={{ borderColor: "divider" }}
                  >
                    {s.label}
                  </Button>
                ))}
              </Stack>
            </Box>
          ) : null}

          <Box
            sx={{
              display: "grid",
              gap: 1.5,
              gridTemplateColumns: {
                xs: "1fr 1fr",
                sm: "repeat(3, 1fr)",
                md: `repeat(${Math.min(visibleCards.length || 1, 5)}, minmax(0, 1fr))`,
              },
            }}
          >
            {visibleCards.map((card) => (
              <Card
                key={card.key}
                component={Link}
                href={card.href}
                sx={{
                  textDecoration: "none",
                  transition: "border-color 0.15s ease",
                  "&:hover": { borderColor: "primary.main" },
                }}
              >
                <CardContent sx={{ py: 1.75, "&:last-child": { pb: 1.75 } }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                    <Box>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ display: "block", mb: 0.5 }}
                      >
                        {card.label}
                      </Typography>
                      <Typography variant="h5" sx={{ fontWeight: 700, lineHeight: 1.1 }}>
                        {loading || !stats ? <Skeleton width={36} /> : stats[card.key]}
                      </Typography>
                    </Box>
                    {card.icon}
                  </Stack>
                </CardContent>
              </Card>
            ))}
          </Box>
        </Stack>
      </Box>

      <Box
        sx={{
          display: "grid",
          gap: 2.5,
          gridTemplateColumns: { xs: "1fr", md: "1fr 1fr", lg: "1fr 1fr 1fr" },
          mb: 2.5,
        }}
      >
        <Card>
          <CardContent>
            <SectionTitle>Activity</SectionTitle>
            {loading && !stats ? (
              <Skeleton height={160} />
            ) : (
              <>
                <DonutChart
                  segments={stats?.module_mix || []}
                  size={140}
                  centerLabel={String(
                    (stats?.module_mix || []).reduce((a, b) => a + b.value, 0)
                  )}
                  centerSub="total"
                />
                <LegendList items={stats?.module_mix || []} />
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <SectionTitle>Leave</SectionTitle>
            {loading && !stats ? (
              <Skeleton height={160} />
            ) : leaveSeg.length ? (
              <>
                <DonutChart
                  segments={leaveSeg}
                  size={140}
                  centerLabel={String(stats?.pending_leaves ?? 0)}
                  centerSub="pending"
                />
                <LegendList items={leaveSeg} />
              </>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ py: 6 }} align="center">
                No leave data
              </Typography>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <SectionTitle>Journal entries</SectionTitle>
            {loading && !stats ? (
              <Skeleton height={160} />
            ) : journalSeg.length ? (
              <>
                <DonutChart
                  segments={journalSeg}
                  size={140}
                  centerLabel={String(journalSeg.reduce((a, b) => a + b.value, 0))}
                  centerSub="journals"
                />
                <LegendList items={journalSeg} />
              </>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ py: 6 }} align="center">
                No journals
              </Typography>
            )}
          </CardContent>
        </Card>
      </Box>

      <Box
        sx={{
          display: "grid",
          gap: 2.5,
          gridTemplateColumns: { xs: "1fr", md: "1.35fr 1fr" },
          mb: 2.5,
        }}
      >
        <Card>
          <CardContent>
            <SectionTitle>6-month trend</SectionTitle>
            {loading && !stats ? (
              <Skeleton height={180} />
            ) : (
              <DualLineChart series={stats?.trend_6m || []} />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <SectionTitle>Attendance</SectionTitle>
            {loading && !stats ? (
              <Skeleton height={180} />
            ) : attendanceBars.some((b) => b.value > 0) ? (
              <BarChart series={attendanceBars} color="#4BA3C7" />
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ py: 6 }} align="center">
                No attendance this month
              </Typography>
            )}
          </CardContent>
        </Card>
      </Box>

      <Box
        sx={{
          display: "grid",
          gap: 2.5,
          gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
        }}
      >
        <Card>
          <CardContent>
            <SectionTitle>Budget</SectionTitle>
            {loading && !stats ? (
              <Skeleton height={64} />
            ) : (
              <>
                <Stack direction="row" justifyContent="space-between" alignItems="baseline" mb={1}>
                  <Typography variant="h5" fontWeight={700}>
                    {stats?.budget?.pct ?? 0}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {stats?.budget?.utilized ?? "0"} / {stats?.budget?.total ?? "0"}
                  </Typography>
                </Stack>
                <LinearProgress
                  variant="determinate"
                  value={Math.min(100, stats?.budget?.pct ?? 0)}
                  sx={{ height: 8, borderRadius: 4 }}
                  color={
                    (stats?.budget?.pct ?? 0) >= 90
                      ? "warning"
                      : (stats?.budget?.pct ?? 0) >= 70
                        ? "primary"
                        : "success"
                  }
                />
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <SectionTitle>AP status</SectionTitle>
            {loading && !stats ? (
              <Skeleton height={120} />
            ) : apSeg.length ? (
              <BarChart
                series={apSeg.map((s) => ({ label: s.label, value: s.value }))}
                color="#E08A5A"
                height={140}
              />
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ py: 4 }} align="center">
                No invoices
              </Typography>
            )}
          </CardContent>
        </Card>
      </Box>
    </ModuleGate>
  );
}
