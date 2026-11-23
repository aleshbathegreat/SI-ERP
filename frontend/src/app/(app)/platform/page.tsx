"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Skeleton,
  Stack,
  Typography,
} from "@mui/material";
import BusinessIcon from "@mui/icons-material/Business";
import EmailIcon from "@mui/icons-material/Email";
import CreditCardIcon from "@mui/icons-material/CreditCard";
import InventoryIcon from "@mui/icons-material/Inventory2";
import SentimentSatisfiedAltIcon from "@mui/icons-material/SentimentSatisfiedAlt";
import SentimentNeutralIcon from "@mui/icons-material/SentimentNeutral";
import SentimentDissatisfiedIcon from "@mui/icons-material/SentimentDissatisfied";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import PlatformGate from "@/components/PlatformGate";
import PageHeader from "@/components/PageHeader";
import {
  BarChart,
  DonutChart,
  LegendList,
  MeterRing,
} from "@/components/dashboard/Charts";
import api from "@/lib/api";

type Sentiment = { tone: string; title: string; detail: string };
type PkgStat = {
  id: number;
  name: string;
  code: string;
  price: string;
  interval: string;
  module_count: number;
  tenants: number;
  max_functional_users: number;
  max_ess_users: number;
};

type Overview = {
  tenants: number;
  tenants_active: number;
  tenants_trial: number;
  tenants_paid: number;
  tenants_past_due?: number;
  packages: number;
  platform_smtp_active: boolean;
  platform_payfast_ready: boolean;
  open_tickets?: number;
  unpaid_invoices?: number;
  health_score?: number;
  plan_mix?: { label: string; value: number; color?: string }[];
  status_mix?: { label: string; value: number; color?: string }[];
  package_stats?: PkgStat[];
  sentiments?: Sentiment[];
  recent_tenants: {
    id: number;
    name: string;
    code: string;
    plan: string;
    plan_status: string;
    brand_name?: string;
  }[];
};

const STATUS_COLORS: Record<string, string> = {
  active: "#4CAF7A",
  past_due: "#D4A017",
  canceled: "#F04438",
  cancelled: "#F04438",
  trial: "#4BA3C7",
  monthly: "#4BA3C7",
  annual: "#E08A5A",
  month: "#4BA3C7",
  year: "#E08A5A",
};

function toneIcon(tone: string) {
  if (tone === "positive") return <SentimentSatisfiedAltIcon color="success" />;
  if (tone === "attention") return <SentimentDissatisfiedIcon color="warning" />;
  return <SentimentNeutralIcon color="primary" />;
}

function toneBg(tone: string) {
  if (tone === "positive") return "rgba(76, 175, 122, 0.12)";
  if (tone === "attention") return "rgba(212, 160, 23, 0.14)";
  return "rgba(75, 163, 199, 0.10)";
}

function Kpi({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <Card variant="outlined" sx={{ flex: 1, minWidth: 140 }}>
      <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
        <Typography variant="caption" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="h5" fontWeight={700}>
          {value}
        </Typography>
        {hint ? (
          <Typography variant="caption" color="text.secondary">
            {hint}
          </Typography>
        ) : null}
      </CardContent>
    </Card>
  );
}

export default function PlatformDashboardPage() {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<Overview>("/platform/overview/")
      .then((r) => setData(r.data))
      .catch(() => setError("Unable to load platform overview"))
      .finally(() => setLoading(false));
  }, []);

  const planSeg = useMemo(
    () =>
      (data?.plan_mix || []).map((s) => ({
        ...s,
        color: STATUS_COLORS[s.label] || "#4BA3C7",
      })),
    [data]
  );
  const statusSeg = useMemo(
    () =>
      (data?.status_mix || []).map((s) => ({
        ...s,
        color: STATUS_COLORS[s.label] || "#9AA8B6",
      })),
    [data]
  );

  const health = data?.health_score ?? 100;
  const healthLabel =
    health >= 80 ? "Platform healthy" : health >= 55 ? "Needs attention" : "Action required";

  return (
    <PlatformGate capability="overview">
      <PageHeader
        title="SI-ERP platform control center"
        subtitle="Tenants, packages, billing, and support"
      />
      {error ? (
        <Typography color="error">{error}</Typography>
      ) : (
        <Stack spacing={2}>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Chip
              icon={<TrendingUpIcon />}
              label={healthLabel}
              color={health >= 80 ? "success" : health >= 55 ? "warning" : "error"}
              variant="outlined"
            />
            <Chip
              icon={<EmailIcon />}
              color={data?.platform_smtp_active ? "success" : "warning"}
              label={
                data?.platform_smtp_active
                  ? "Platform SMTP active"
                  : "Platform SMTP inactive"
              }
            />
            <Chip
              icon={<CreditCardIcon />}
              color={data?.platform_payfast_ready ? "success" : "warning"}
              label={
                data?.platform_payfast_ready
                  ? "Platform PayFast ready"
                  : "Platform PayFast not configured"
              }
            />
          </Stack>

          <Box
            sx={{
              display: "grid",
              gap: 2,
              gridTemplateColumns: { xs: "1fr", md: "200px 1fr" },
            }}
          >
            <Card
              sx={{
                background: (t) =>
                  `linear-gradient(145deg, ${t.palette.background.paper} 0%, ${
                    t.palette.mode === "dark" ? "#1a2430" : "#e8f1f6"
                  } 100%)`,
              }}
            >
              <CardContent>
                {loading && !data ? (
                  <Skeleton variant="circular" width={120} height={120} sx={{ mx: "auto" }} />
                ) : (
                  <MeterRing value={health} label="Health" />
                )}
                <Typography
                  variant="body2"
                  color="text.secondary"
                  align="center"
                  sx={{ mt: 1 }}
                >
                  Past-due · tickets · invoices · rails
                </Typography>
              </CardContent>
            </Card>

            <Card>
              <CardContent>
                <Typography variant="subtitle1" fontWeight={700} gutterBottom>
                  Platform sentiment
                </Typography>
                {loading && !data ? (
                  <Stack spacing={1}>
                    <Skeleton height={48} />
                    <Skeleton height={48} />
                  </Stack>
                ) : (
                  <Box
                    sx={{
                      display: "grid",
                      gap: 1.25,
                      gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
                    }}
                  >
                    {(data?.sentiments || []).map((s) => (
                      <Box
                        key={s.title}
                        sx={{
                          p: 1.5,
                          borderRadius: 2,
                          bgcolor: toneBg(s.tone),
                          border: "1px solid",
                          borderColor: "divider",
                        }}
                      >
                        <Stack direction="row" spacing={1} alignItems="flex-start">
                          {toneIcon(s.tone)}
                          <Box sx={{ minWidth: 0 }}>
                            <Typography variant="subtitle2" fontWeight={700}>
                              {s.title}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              {s.detail}
                            </Typography>
                          </Box>
                        </Stack>
                      </Box>
                    ))}
                  </Box>
                )}
              </CardContent>
            </Card>
          </Box>

          <Stack direction="row" spacing={1.5} flexWrap="wrap" useFlexGap>
            <Kpi label="Tenants" value={loading ? "—" : String(data?.tenants ?? "—")} />
            <Kpi label="Active" value={loading ? "—" : String(data?.tenants_active ?? "—")} />
            <Kpi label="On trial" value={loading ? "—" : String(data?.tenants_trial ?? "—")} />
            <Kpi label="Past due" value={loading ? "—" : String(data?.tenants_past_due ?? "—")} />
            <Kpi label="Packages" value={loading ? "—" : String(data?.packages ?? "—")} />
            <Kpi label="Open tickets" value={loading ? "—" : String(data?.open_tickets ?? "—")} />
            <Kpi
              label="Unpaid invoices"
              value={loading ? "—" : String(data?.unpaid_invoices ?? "—")}
            />
          </Stack>

          <Box
            sx={{
              display: "grid",
              gap: 2,
              gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
            }}
          >
            <Card>
              <CardContent>
                <Typography variant="subtitle1" fontWeight={700} gutterBottom>
                  Plan mix
                </Typography>
                {loading && !data ? (
                  <Skeleton height={160} />
                ) : planSeg.length ? (
                  <>
                    <DonutChart
                      segments={planSeg}
                      centerLabel={String(data?.tenants ?? 0)}
                      centerSub="tenants"
                    />
                    <LegendList items={planSeg} />
                  </>
                ) : (
                  <Typography variant="body2" color="text.secondary" align="center" sx={{ py: 4 }}>
                    No tenants yet
                  </Typography>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardContent>
                <Typography variant="subtitle1" fontWeight={700} gutterBottom>
                  Subscription status
                </Typography>
                {loading && !data ? (
                  <Skeleton height={160} />
                ) : statusSeg.length ? (
                  <>
                    <DonutChart
                      segments={statusSeg}
                      centerLabel={String(data?.tenants_past_due ?? 0)}
                      centerSub="past due"
                    />
                    <LegendList items={statusSeg} />
                  </>
                ) : (
                  <Typography variant="body2" color="text.secondary" align="center" sx={{ py: 4 }}>
                    No status data
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Box>

          <Card>
            <CardContent>
              <Stack
                direction={{ xs: "column", sm: "row" }}
                justifyContent="space-between"
                alignItems={{ xs: "stretch", sm: "center" }}
                spacing={1}
                mb={1.5}
              >
                <Box>
                  <Typography variant="subtitle1" fontWeight={700}>
                    Packages · modules & seats
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Core shell always on · assign Finance / HR / Payroll / Billing per plan
                  </Typography>
                </Box>
                <Button
                  component={Link}
                  href="/platform/packages"
                  variant="contained"
                  startIcon={<InventoryIcon />}
                >
                  Manage packages
                </Button>
              </Stack>
              {loading && !data ? (
                <Skeleton height={120} />
              ) : (
                <Box
                  sx={{
                    display: "grid",
                    gap: 1.5,
                    gridTemplateColumns: {
                      xs: "1fr",
                      sm: "1fr 1fr",
                      md: "repeat(3, 1fr)",
                    },
                  }}
                >
                  {(data?.package_stats || []).map((p) => (
                    <Box
                      key={p.id}
                      sx={{
                        p: 1.5,
                        borderRadius: 2,
                        border: "1px solid",
                        borderColor: "divider",
                      }}
                    >
                      <Stack direction="row" justifyContent="space-between" mb={0.5}>
                        <Typography fontWeight={700}>{p.name}</Typography>
                        <Chip size="small" label={p.interval} />
                      </Stack>
                      <Typography variant="body2" color="text.secondary">
                        {p.price} · {p.max_functional_users}F / {p.max_ess_users} ESS
                      </Typography>
                      <Stack direction="row" spacing={1} mt={1} flexWrap="wrap" useFlexGap>
                        <Chip
                          size="small"
                          color="primary"
                          variant="outlined"
                          label={`${p.module_count} modules`}
                        />
                        <Chip
                          size="small"
                          variant="outlined"
                          label={`${p.tenants} tenant${p.tenants === 1 ? "" : "s"}`}
                        />
                      </Stack>
                    </Box>
                  ))}
                  {!data?.package_stats?.length ? (
                    <Typography color="text.secondary">No active packages.</Typography>
                  ) : null}
                </Box>
              )}
              {(data?.package_stats || []).some((p) => p.tenants > 0) ? (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="caption" color="text.secondary" display="block" mb={1}>
                    Tenants per package
                  </Typography>
                  <BarChart
                    series={(data?.package_stats || []).map((p) => ({
                      label: p.code,
                      value: p.tenants,
                    }))}
                    color="#4BA3C7"
                    height={140}
                  />
                </Box>
              ) : null}
            </CardContent>
          </Card>

          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} flexWrap="wrap" useFlexGap>
            <Button
              component={Link}
              href="/platform/packages"
              variant="contained"
              startIcon={<InventoryIcon />}
            >
              Packages
            </Button>
            <Button
              component={Link}
              href="/platform/tenants"
              variant="outlined"
              startIcon={<BusinessIcon />}
            >
              Tenants
            </Button>
            <Button component={Link} href="/platform/invoices" variant="outlined">
              Invoices
            </Button>
            <Button component={Link} href="/platform/tickets" variant="outlined">
              Tickets
            </Button>
            <Button component={Link} href="/platform/staff" variant="outlined">
              Staff
            </Button>
            <Button
              component={Link}
              href="/settings/platform-smtp"
              variant="outlined"
              startIcon={<EmailIcon />}
            >
              Platform SMTP
            </Button>
            <Button
              component={Link}
              href="/settings/platform-payfast"
              variant="outlined"
              startIcon={<CreditCardIcon />}
            >
              Platform PayFast
            </Button>
            <Button component={Link} href="/platform/domains" variant="text">
              Domains
            </Button>
          </Stack>

          <Card variant="outlined">
            <CardContent>
              <Stack direction="row" alignItems="center" spacing={1} mb={1.5}>
                <BusinessIcon color="primary" />
                <Typography variant="h6">Recent tenants</Typography>
              </Stack>
              <Stack spacing={1}>
                {(data?.recent_tenants || []).map((t) => (
                  <Box
                    key={t.id}
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      gap: 2,
                      py: 0.75,
                      borderBottom: "1px solid",
                      borderColor: "divider",
                    }}
                  >
                    <Box>
                      <Typography fontWeight={600}>{t.brand_name || t.name}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {t.code}
                      </Typography>
                    </Box>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Chip size="small" label={t.plan} />
                      <Chip
                        size="small"
                        variant="outlined"
                        color={t.plan_status === "active" ? "success" : "default"}
                        label={t.plan_status}
                      />
                    </Stack>
                  </Box>
                ))}
                {!data?.recent_tenants?.length ? (
                  <Typography color="text.secondary">No tenants yet.</Typography>
                ) : null}
              </Stack>
            </CardContent>
          </Card>

          <Typography variant="body2" color="text.secondary">
            Package module assignment controls which product modules tenants can access. Core shell
            (dashboard, approvals, ESS, settings) stays on for every plan.
          </Typography>
        </Stack>
      )}
    </PlatformGate>
  );
}
