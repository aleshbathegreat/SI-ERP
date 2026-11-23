"use client";

import { useEffect, useState } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Stack,
  Tab,
  Tabs,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { useSnackbar } from "notistack";
import ModuleGate from "@/components/ModuleGate";
import PageHeader from "@/components/PageHeader";
import api from "@/lib/api";
import { formatMoney } from "@/lib/format";

type MoneyRow = Record<string, string | number | undefined>;

type ReportPayload = {
  accounts?: number;
  vendors?: number;
  open_journals?: number;
  budget_total?: number | string;
  budget_utilized?: number | string;
  ap_open?: number;
  assets?: number;
  investments?: number;
  trial_balance?: {
    lines?: MoneyRow[];
    total_debit?: string;
    total_credit?: string;
    balanced?: boolean;
  };
  income_statement?: {
    lines?: MoneyRow[];
    total_income?: string;
    total_expense?: string;
    surplus_deficit?: string;
  };
  balance_sheet?: {
    assets?: MoneyRow[];
    liabilities?: MoneyRow[];
    equity?: MoneyRow[];
    total_assets?: string;
    total_liabilities?: string;
    total_equity?: string;
  };
  cash_position?: {
    banks?: MoneyRow[];
    total_opening?: string;
    total_balance?: string;
  };
  cash_flow?: {
    year?: number;
    operating?: string;
    investing?: string;
    financing?: string;
    net_change?: string;
    closing_cash?: string;
    lines?: MoneyRow[];
    note?: string;
  };
  ap_ageing?: {
    invoices?: MoneyRow[];
    buckets?: Record<string, string>;
    total_open?: string;
  };
  budget_vs_actual?: {
    fiscal_year?: number;
    lines?: MoneyRow[];
    total_budget?: string;
    total_actual?: string;
    total_variance?: string;
  };
  ar_ageing?: {
    invoices?: MoneyRow[];
    buckets?: Record<string, string>;
    total_open?: string;
  };
  stock_valuation?: {
    lines?: MoneyRow[];
    total_value?: string;
  };
  wht_register?: {
    lines?: MoneyRow[];
    total_gross?: string;
    total_wht?: string;
    challans?: MoneyRow[];
  };
  payroll_register?: {
    lines?: MoneyRow[];
    total_gross?: string;
    total_net?: string;
  };
};

type SavedReport = {
  id: number;
  name: string;
  report_key: string;
  params?: { as_of?: string; year?: string };
};

// Tab index → backend report key (for export / saved views)
const TAB_REPORT_KEYS: Record<number, string> = {
  0: "trial_balance",
  1: "income_statement",
  2: "balance_sheet",
  5: "ap_ageing",
  7: "ar_ageing",
  8: "stock_valuation",
  9: "wht_register",
  10: "payroll_register",
};

function MoneyTable({
  rows,
  columns,
}: {
  rows: MoneyRow[];
  columns: { key: string; label: string; align?: "right" | "left" }[];
}) {
  if (!rows?.length) {
    return (
      <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
        No rows for this period.
      </Typography>
    );
  }
  return (
    <Table size="small">
      <TableHead>
        <TableRow>
          {columns.map((c) => (
            <TableCell key={c.key} align={c.align || "left"}>
              {c.label}
            </TableCell>
          ))}
        </TableRow>
      </TableHead>
      <TableBody>
        {rows.map((r, i) => (
          <TableRow key={i}>
            {columns.map((c) => {
              const raw = r[c.key];
              const isMoney =
                c.align === "right" ||
                /debit|credit|amount|balance|total|income|expense|surplus|opening|closing|operating|investing|financing|net|bucket|open/i.test(
                  c.key
                );
              return (
                <TableCell key={c.key} align={c.align || "left"}>
                  {raw == null || raw === ""
                    ? "—"
                    : isMoney && !Number.isNaN(Number(raw))
                      ? formatMoney(raw)
                      : String(raw)}
                </TableCell>
              );
            })}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export default function FinanceReportsPage() {
  const [data, setData] = useState<ReportPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState(0);
  const [asOf, setAsOf] = useState("");
  const [year, setYear] = useState(String(new Date().getFullYear()));

  const [saved, setSaved] = useState<SavedReport[]>([]);
  const [saveName, setSaveName] = useState("");
  const { enqueueSnackbar } = useSnackbar();

  const load = (over?: { as_of?: string; year?: string }) => {
    setLoading(true);
    const params: Record<string, string> = {};
    const a = over?.as_of ?? asOf;
    const y = over?.year ?? year;
    if (a) params.as_of = a;
    if (y) params.year = y;
    api
      .get("/finance/reports/", { params })
      .then((r) => setData(r.data))
      .finally(() => setLoading(false));
  };

  const loadSaved = () =>
    api
      .get("/finance/saved-reports/")
      .then((r) => setSaved(Array.isArray(r.data) ? r.data : r.data?.results || []))
      .catch(() => setSaved([]));

  useEffect(() => {
    load();
    loadSaved();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const reportKey = TAB_REPORT_KEYS[tab];

  const download = async (fmt: "xlsx" | "csv") => {
    if (!reportKey) return;
    try {
      const params: Record<string, string> = { report: reportKey, export: fmt };
      if (asOf) params.as_of = asOf;
      if (year) params.year = year;
      const res = await api.get("/finance/reports/run/", {
        params,
        responseType: "blob",
      });
      const url = URL.createObjectURL(res.data as Blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${reportKey}.${fmt}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      enqueueSnackbar("Export failed", { variant: "error" });
    }
  };

  const saveView = async () => {
    if (!reportKey || !saveName.trim()) return;
    try {
      await api.post("/finance/saved-reports/", {
        name: saveName.trim(),
        report_key: reportKey,
        params: { as_of: asOf, year },
      });
      setSaveName("");
      enqueueSnackbar("Report view saved", { variant: "success" });
      loadSaved();
    } catch {
      enqueueSnackbar("Could not save view", { variant: "error" });
    }
  };

  const applySaved = (s: SavedReport) => {
    const tabIdx = Object.entries(TAB_REPORT_KEYS).find(([, k]) => k === s.report_key)?.[0];
    if (tabIdx !== undefined) setTab(Number(tabIdx));
    const a = s.params?.as_of || "";
    const y = s.params?.year || year;
    setAsOf(a);
    setYear(y);
    load({ as_of: a, year: y });
  };

  const kpis = [
    ["accounts", "GL accounts"],
    ["vendors", "Vendors"],
    ["open_journals", "Unposted / in LoA JVs"],
    ["budget_total", "Budget total"],
    ["budget_utilized", "Budget utilized"],
    ["ap_open", "Open AP bills"],
    ["assets", "Fixed assets"],
    ["investments", "Investments"],
  ] as const;

  const tb = data?.trial_balance;
  const is = data?.income_statement;
  const bs = data?.balance_sheet;
  const cash = data?.cash_position;
  const cf = data?.cash_flow;
  const ageing = data?.ap_ageing;
  const bva = data?.budget_vs_actual;
  const arAgeing = data?.ar_ageing;
  const stock = data?.stock_valuation;
  const wht = data?.wht_register;
  const payroll = data?.payroll_register;

  return (
    <ModuleGate module="finance.reports">
      <PageHeader
        title="Statutory finance reports"
        subtitle="TB · P&L · BS · cash · AP/AR ageing · stock valuation · WHT register · payroll register"
        moduleKey="finance.reports"
      />
      <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ mb: 2 }} alignItems="center">
        <TextField
          label="As of"
          type="date"
          size="small"
          InputLabelProps={{ shrink: true }}
          value={asOf}
          onChange={(e) => setAsOf(e.target.value)}
        />
        <TextField
          label="Fiscal year"
          type="number"
          size="small"
          value={year}
          onChange={(e) => setYear(e.target.value)}
          sx={{ width: 120 }}
        />
        <Button variant="contained" size="small" onClick={() => load()}>
          Apply
        </Button>
        <Button
          size="small"
          disabled={!reportKey}
          onClick={() => download("xlsx")}
          title={reportKey ? "Download current report as Excel" : "Export not available for this tab"}
        >
          Excel
        </Button>
        <Button size="small" disabled={!reportKey} onClick={() => download("csv")}>
          CSV
        </Button>
      </Stack>
      <Stack
        direction="row"
        spacing={1}
        sx={{ mb: 2 }}
        alignItems="center"
        flexWrap="wrap"
        useFlexGap
      >
        <TextField
          size="small"
          label="Save current view as"
          value={saveName}
          onChange={(e) => setSaveName(e.target.value)}
        />
        <Button size="small" disabled={!reportKey || !saveName.trim()} onClick={saveView}>
          Save view
        </Button>
        {saved.map((s) => (
          <Chip
            key={s.id}
            size="small"
            variant="outlined"
            label={s.name}
            onClick={() => applySaved(s)}
          />
        ))}
      </Stack>

      {loading ? (
        <Stack alignItems="center" p={6}>
          <CircularProgress />
        </Stack>
      ) : (
        <>
          <Box
            sx={{
              display: "grid",
              gap: 2,
              gridTemplateColumns: { xs: "1fr", md: "repeat(4, 1fr)" },
              mb: 3,
            }}
          >
            {kpis.map(([key, label]) => (
              <Card key={key} variant="outlined">
                <CardContent>
                  <Typography variant="body2" color="text.secondary">
                    {label}
                  </Typography>
                  <Typography variant="h5">{data?.[key] ?? 0}</Typography>
                </CardContent>
              </Card>
            ))}
          </Box>

          <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }} variant="scrollable">
            <Tab label="Trial balance" />
            <Tab label="Profit and loss" />
            <Tab label="Balance sheet" />
            <Tab label="Cash" />
            <Tab label="Cash flow" />
            <Tab label="Bills you owe" />
            <Tab label="Budget vs actual" />
            <Tab label="Customers owe you" />
            <Tab label="Stock valuation" />
            <Tab label="WHT register" />
            <Tab label="Payroll register" />
          </Tabs>

          <Card variant="outlined">
            <CardContent>
              {tab === 0 && (
                <Stack spacing={1}>
                  <MoneyTable
                    rows={tb?.lines || []}
                    columns={[
                      { key: "code", label: "Code" },
                      { key: "name", label: "Account" },
                      { key: "account_type", label: "Type" },
                      { key: "debit", label: "Debit", align: "right" },
                      { key: "credit", label: "Credit", align: "right" },
                    ]}
                  />
                  <Typography variant="body2">
                    Totals Dr {tb?.total_debit ?? "0"} / Cr {tb?.total_credit ?? "0"}
                    {tb?.balanced != null ? ` · ${tb.balanced ? "Balanced" : "Out of balance"}` : ""}
                  </Typography>
                </Stack>
              )}
              {tab === 1 && (
                <Stack spacing={1}>
                  <MoneyTable
                    rows={is?.lines || []}
                    columns={[
                      { key: "code", label: "Code" },
                      { key: "name", label: "Account" },
                      { key: "account_type", label: "Type" },
                      { key: "amount", label: "Amount", align: "right" },
                    ]}
                  />
                  <Typography variant="body2">
                    Income {is?.total_income ?? "0"} · Expense {is?.total_expense ?? "0"}
                  </Typography>
                  <Typography variant="h6">
                    Surplus/(Deficit): {is?.surplus_deficit ?? "—"}
                  </Typography>
                </Stack>
              )}
              {tab === 2 && (
                <Stack spacing={2}>
                  <Typography variant="subtitle2">Assets · {bs?.total_assets ?? "0"}</Typography>
                  <MoneyTable
                    rows={bs?.assets || []}
                    columns={[
                      { key: "code", label: "Code" },
                      { key: "name", label: "Account" },
                      { key: "amount", label: "Amount", align: "right" },
                    ]}
                  />
                  <Typography variant="subtitle2">
                    Liabilities · {bs?.total_liabilities ?? "0"}
                  </Typography>
                  <MoneyTable
                    rows={bs?.liabilities || []}
                    columns={[
                      { key: "code", label: "Code" },
                      { key: "name", label: "Account" },
                      { key: "amount", label: "Amount", align: "right" },
                    ]}
                  />
                  <Typography variant="subtitle2">Equity · {bs?.total_equity ?? "0"}</Typography>
                  <MoneyTable
                    rows={bs?.equity || []}
                    columns={[
                      { key: "code", label: "Code" },
                      { key: "name", label: "Account" },
                      { key: "amount", label: "Amount", align: "right" },
                    ]}
                  />
                </Stack>
              )}
              {tab === 3 && (
                <Stack spacing={1}>
                  <MoneyTable
                    rows={cash?.banks || []}
                    columns={[
                      { key: "name", label: "Account" },
                      { key: "bank_name", label: "Bank" },
                      { key: "account_no", label: "No." },
                      { key: "currency", label: "CCY" },
                      { key: "opening_balance", label: "Opening", align: "right" },
                      { key: "current_balance", label: "Current", align: "right" },
                    ]}
                  />
                  <Typography variant="body2">
                    Total balance: {cash?.total_balance ?? cash?.total_opening ?? "0"}
                  </Typography>
                </Stack>
              )}
              {tab === 4 && (
                <Stack spacing={1}>
                  <Typography variant="body2" color="text.secondary">
                    {cf?.note || "Cash flow"} · FY {cf?.year ?? year}
                  </Typography>
                  <Typography variant="body2">
                    Operating {cf?.operating ?? "0"} · Investing {cf?.investing ?? "0"} · Financing{" "}
                    {cf?.financing ?? "0"}
                  </Typography>
                  <Typography variant="h6">
                    Net change {cf?.net_change ?? "—"} · Closing cash {cf?.closing_cash ?? "—"}
                  </Typography>
                  <MoneyTable
                    rows={cf?.lines || []}
                    columns={[
                      { key: "section", label: "Section" },
                      { key: "code", label: "Code" },
                      { key: "name", label: "Account" },
                      { key: "amount", label: "Amount", align: "right" },
                    ]}
                  />
                </Stack>
              )}
              {tab === 5 && (
                <Stack spacing={1}>
                  <Typography variant="body2">
                    Open AP {ageing?.total_open ?? "0"}
                    {ageing?.buckets
                      ? ` · current ${ageing.buckets.current} · 1–30 ${ageing.buckets.days_1_30} · 31–60 ${ageing.buckets.days_31_60} · 61–90 ${ageing.buckets.days_61_90} · 90+ ${ageing.buckets.days_90_plus}`
                      : ""}
                  </Typography>
                  <MoneyTable
                    rows={ageing?.invoices || []}
                    columns={[
                      { key: "vendor", label: "Vendor" },
                      { key: "invoice_no", label: "Invoice" },
                      { key: "due_date", label: "Due" },
                      { key: "bucket", label: "Bucket" },
                      { key: "amount", label: "Amount", align: "right" },
                    ]}
                  />
                </Stack>
              )}
              {tab === 6 && (
                <Stack spacing={1}>
                  <Typography variant="body2" color="text.secondary">
                    FY {bva?.fiscal_year ?? year} · from posted expense journals by cost centre
                  </Typography>
                  <MoneyTable
                    rows={bva?.lines || []}
                    columns={[
                      { key: "name", label: "Budget" },
                      { key: "cost_center", label: "CC" },
                      { key: "status", label: "Status" },
                      { key: "budget", label: "Budget", align: "right" },
                      { key: "actual", label: "Actual", align: "right" },
                      { key: "variance", label: "Variance", align: "right" },
                      { key: "utilization_pct", label: "Util %", align: "right" },
                    ]}
                  />
                  <Typography variant="body2">
                    Total budget {formatMoney(bva?.total_budget)} · actual{" "}
                    {formatMoney(bva?.total_actual)} · variance{" "}
                    {formatMoney(bva?.total_variance)}
                  </Typography>
                </Stack>
              )}
              {tab === 7 && (
                <Stack spacing={1}>
                  <Typography variant="body2">
                    Open AR {arAgeing?.total_open ?? "0"}
                    {arAgeing?.buckets
                      ? ` · current ${arAgeing.buckets.current} · 1–30 ${arAgeing.buckets.days_1_30} · 31–60 ${arAgeing.buckets.days_31_60} · 61–90 ${arAgeing.buckets.days_61_90} · 90+ ${arAgeing.buckets.days_90_plus}`
                      : ""}
                  </Typography>
                  <MoneyTable
                    rows={arAgeing?.invoices || []}
                    columns={[
                      { key: "customer", label: "Customer" },
                      { key: "invoice_no", label: "Invoice" },
                      { key: "due_date", label: "Due" },
                      { key: "bucket", label: "Bucket" },
                      { key: "amount", label: "Open", align: "right" },
                    ]}
                  />
                </Stack>
              )}
              {tab === 8 && (
                <Stack spacing={1}>
                  <MoneyTable
                    rows={stock?.lines || []}
                    columns={[
                      { key: "sku", label: "SKU" },
                      { key: "name", label: "Item" },
                      { key: "warehouse", label: "Warehouse" },
                      { key: "qty", label: "Qty" },
                      { key: "unit_cost", label: "Unit cost", align: "right" },
                      { key: "amount", label: "Value", align: "right" },
                    ]}
                  />
                  <Typography variant="h6">
                    Total stock value: {formatMoney(stock?.total_value)}
                  </Typography>
                </Stack>
              )}
              {tab === 9 && (
                <Stack spacing={1}>
                  <MoneyTable
                    rows={wht?.lines || []}
                    columns={[
                      { key: "invoice_date", label: "Date" },
                      { key: "vendor", label: "Vendor" },
                      { key: "ntn", label: "NTN" },
                      { key: "invoice_no", label: "Invoice" },
                      { key: "gross", label: "Gross", align: "right" },
                      { key: "wht_amount", label: "WHT", align: "right" },
                    ]}
                  />
                  <Typography variant="body2">
                    Gross {formatMoney(wht?.total_gross)} · WHT {formatMoney(wht?.total_wht)}
                  </Typography>
                  <Typography variant="subtitle2">Challans</Typography>
                  <MoneyTable
                    rows={wht?.challans || []}
                    columns={[
                      { key: "challan_no", label: "Challan" },
                      { key: "period", label: "Period" },
                      { key: "amount", label: "Amount", align: "right" },
                      { key: "status", label: "Status" },
                    ]}
                  />
                </Stack>
              )}
              {tab === 10 && (
                <Stack spacing={1}>
                  <MoneyTable
                    rows={payroll?.lines || []}
                    columns={[
                      { key: "period", label: "Period" },
                      { key: "headcount", label: "Staff" },
                      { key: "gross", label: "Gross", align: "right" },
                      { key: "deductions", label: "Deductions", align: "right" },
                      { key: "tax", label: "Income tax", align: "right" },
                      { key: "employer_cost", label: "Employer cost", align: "right" },
                      { key: "net", label: "Net pay", align: "right" },
                    ]}
                  />
                  <Typography variant="body2">
                    Gross {formatMoney(payroll?.total_gross)} · Net{" "}
                    {formatMoney(payroll?.total_net)}
                  </Typography>
                </Stack>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </ModuleGate>
  );
}
