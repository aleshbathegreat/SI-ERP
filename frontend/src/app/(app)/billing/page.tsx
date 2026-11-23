"use client";

import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import api from "@/lib/api";
import ModuleGate from "@/components/ModuleGate";
import { usePermissions } from "@/hooks/usePermissions";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { setOrganization } from "@/store/auth/slice";
import type { Organization } from "@/store/auth/types";
import { useSearchParams } from "next/navigation";

type Plan = {
  id: number;
  name: string;
  code: string;
  price: string;
  interval: string;
  summary: string;
};

type Payment = {
  id: number;
  plan: string;
  amount: string;
  status: string;
  reference: string;
  period_end?: string;
  status_message?: string;
  environment?: string;
  transaction_id?: string;
};

function handoffToPayFast(action: string, fields: Record<string, string>) {
  const form = document.createElement("form");
  form.method = "POST";
  form.action = action;
  form.style.display = "none";
  Object.entries(fields).forEach(([key, value]) => {
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = key;
    input.value = value ?? "";
    form.appendChild(input);
  });
  document.body.appendChild(form);
  form.submit();
}

export default function BillingPage() {
  const { canChange } = usePermissions();
  const dispatch = useAppDispatch();
  const user = useAppSelector((s) => s.auth.user);
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [renewing, setRenewing] = useState<string | null>(null);
  const [org, setOrg] = useState<Organization | null>(null);
  const [open, setOpen] = useState(true);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [message, setMessage] = useState("");
  const [gatewayReady, setGatewayReady] = useState(false);
  const [environment, setEnvironment] = useState("sandbox");
  const [mobile, setMobile] = useState("");
  const [email, setEmail] = useState("");
  const [inGrace, setInGrace] = useState(false);
  const [daysLock, setDaysLock] = useState<number | null>(null);
  const [invoices, setInvoices] = useState<
    { id: number; invoice_no: string; total: string; status: string; due_date?: string }[]
  >([]);

  const load = () => {
    setLoading(true);
    api
      .get("/saas/billing/")
      .then((r) => {
        setOrg(r.data.organization);
        setOpen(r.data.subscription_open);
        setInGrace(!!r.data.subscription_in_grace);
        setDaysLock(
          typeof r.data.days_until_lock === "number" ? r.data.days_until_lock : null
        );
        setPlans(r.data.plans || []);
        setPayments(r.data.payments || []);
        setInvoices(r.data.invoices || []);
        setGatewayReady(!!r.data.gateway_ready);
        setEnvironment(r.data.environment || "sandbox");
        dispatch(setOrganization(r.data.organization));
        localStorage.setItem("organization", JSON.stringify(r.data.organization));
        localStorage.setItem("subscription_open", String(r.data.subscription_open));
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    setEmail(user?.email || "");
    setMobile(user?.profile?.phone || "");
    load();
  }, []);

  useEffect(() => {
    const pid = searchParams.get("payment");
    if (!pid) return;
    setMessage(`Payment #${pid} — refresh status below after PayFast return.`);
    load();
  }, [searchParams]);

  const payWithPayFast = async (plan: string) => {
    setRenewing(plan);
    setMessage("");
    try {
      const { data } = await api.post("/saas/billing/checkout/", {
        plan,
        mobile: mobile || "03000000000",
        email: email || user?.email,
      });
      if (data.action && data.fields) {
        setMessage("Redirecting to PayFast…");
        handoffToPayFast(data.action, data.fields);
        return;
      }
      setMessage(data.detail || "Checkout failed");
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string; use_checkout?: boolean } } };
      setMessage(err?.response?.data?.detail || "PayFast checkout failed");
    } finally {
      setRenewing(null);
    }
  };

  const demoRenew = async (plan: string) => {
    setRenewing(plan);
    setMessage("");
    try {
      const { data } = await api.post("/saas/billing/renew/", {
        plan,
        demo: true,
      });
      setMessage(`Demo renewed: ${data.payment.reference}`);
      dispatch(setOrganization(data.organization));
      localStorage.setItem("organization", JSON.stringify(data.organization));
      localStorage.setItem("subscription_open", "true");
      load();
    } catch (e: unknown) {
      setMessage(
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          "Renewal failed"
      );
    } finally {
      setRenewing(null);
    }
  };

  if (loading) {
    return (
      <Stack alignItems="center" p={6}>
        <CircularProgress />
      </Stack>
    );
  }

  return (
    <ModuleGate module="billing">
      <Stack spacing={3}>
        <Typography variant="h4">Billing & subscription</Typography>
        {!open ? (
          <Alert severity="warning">
            Subscription/trial ended. Pay below to reopen Finance, HR and Payroll. You can still
            open Support tickets.
          </Alert>
        ) : inGrace ? (
          <Alert severity="warning">
            Grace period — access remains open for {daysLock ?? "a few"} more day(s). Renew now to
            avoid lock.
          </Alert>
        ) : (
          <Alert severity="success">Subscription is open for this tenant.</Alert>
        )}
        <Alert severity={gatewayReady ? "success" : "info"}>
          {gatewayReady
            ? `Premier PayFast ready (${environment}). Checkout posts to the hosted gateway.`
            : "PayFast not configured yet — platform owner must set credentials under Settings → Platform PayFast. Demo renew remains available for testing."}
        </Alert>
        {message ? <Alert severity="info">{message}</Alert> : null}

        <Card>
          <CardContent>
            <Stack spacing={1}>
              <Typography variant="h6">{org?.name}</Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                <Chip label={`Plan: ${org?.plan}`} />
                <Chip label={`Status: ${org?.plan_status}`} variant="outlined" />
                {org?.trial_ends ? <Chip label={`Trial ends: ${org.trial_ends}`} /> : null}
                {org?.subscription_ends ? (
                  <Chip label={`Ends: ${org.subscription_ends}`} color="primary" />
                ) : null}
              </Stack>
            </Stack>
          </CardContent>
        </Card>

        {gatewayReady ? (
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} maxWidth={560}>
            <TextField
              label="Mobile (PayFast)"
              value={mobile}
              onChange={(e) => setMobile(e.target.value)}
              size="small"
              fullWidth
            />
            <TextField
              label="Email (PayFast)"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              size="small"
              fullWidth
            />
          </Stack>
        ) : null}

        <Typography variant="h6">Renew / upgrade</Typography>
        <Box
          sx={{
            display: "grid",
            gap: 2,
            gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
          }}
        >
          {plans.map((p) => (
            <Card key={p.id}>
              <CardContent>
                <Stack spacing={1.5}>
                  <Typography variant="h6">{p.name}</Typography>
                  <Typography variant="h5">
                    PKR {Number(p.price).toLocaleString()}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {p.summary}
                  </Typography>
                  {gatewayReady ? (
                    <Button
                      variant="contained"
                      disabled={!!renewing || !canChange("billing")}
                      onClick={() => payWithPayFast(p.code)}
                    >
                      {renewing === p.code ? "Opening PayFast…" : `Pay with PayFast · ${p.name}`}
                    </Button>
                  ) : (
                    <Button
                      variant="contained"
                      disabled={!!renewing || !canChange("billing")}
                      onClick={() => demoRenew(p.code)}
                    >
                      {renewing === p.code ? "Processing…" : `Demo activate ${p.name}`}
                    </Button>
                  )}
                  {gatewayReady && user?.is_superuser ? (
                    <Button
                      size="small"
                      disabled={!!renewing}
                      onClick={() => demoRenew(p.code)}
                    >
                      Demo renew (superuser)
                    </Button>
                  ) : null}
                </Stack>
              </CardContent>
            </Card>
          ))}
        </Box>

        <Typography variant="h6">Invoices</Typography>
        {invoices.length === 0 ? (
          <Typography color="text.secondary">No SaaS invoices yet.</Typography>
        ) : (
          invoices.map((inv) => (
            <Card key={inv.id}>
              <CardContent>
                <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                  <Typography fontWeight={600}>{inv.invoice_no}</Typography>
                  <Chip size="small" label={inv.status} />
                  <Typography>PKR {Number(inv.total).toLocaleString()}</Typography>
                  {inv.due_date ? (
                    <Typography variant="body2" color="text.secondary">
                      Due {inv.due_date}
                    </Typography>
                  ) : null}
                </Stack>
              </CardContent>
            </Card>
          ))
        )}

        <Typography variant="h6">Payment history</Typography>
        {payments.length === 0 ? (
          <Typography color="text.secondary">No payments yet.</Typography>
        ) : (
          payments.map((pay) => (
            <Card key={pay.id}>
              <CardContent>
                <Typography>
                  {pay.reference} · {pay.plan} · PKR {Number(pay.amount).toLocaleString()} ·{" "}
                  {pay.status}
                  {pay.environment ? ` · ${pay.environment}` : ""}
                </Typography>
                {pay.status_message || pay.transaction_id ? (
                  <Typography variant="body2" color="text.secondary">
                    {[pay.status_message, pay.transaction_id && `txn ${pay.transaction_id}`]
                      .filter(Boolean)
                      .join(" · ")}
                  </Typography>
                ) : null}
              </CardContent>
            </Card>
          ))
        )}
      </Stack>
    </ModuleGate>
  );
}
