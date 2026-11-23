"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Alert,
  Button,
  Chip,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import PaymentsIcon from "@mui/icons-material/Payments";
import FormPageShell from "@/components/crud/FormPageShell";
import DetailPageShell, {
  DetailGrid,
  DetailItem,
  DetailSection,
} from "@/components/crud/DetailPageShell";
import DateTextField, { todayISO } from "@/components/DateTextField";
import ModuleGate from "@/components/ModuleGate";
import WorkflowActions from "@/components/WorkflowActions";
import { useEntityForm, type FormMode } from "@/hooks/useEntityForm";
import { codeNameLabel } from "@/lib/optionLabel";
import { usePermissions } from "@/hooks/usePermissions";
import { useParams, useSearchParams } from "next/navigation";
import { listResource } from "@/lib/crudApi";
import RelationSelect, { RELATIONS } from "@/components/crud/RelationSelect";
import { suggestDocNo, addDaysISO } from "@/lib/docNumbers";
import { formatDate, formatMoney } from "@/lib/format";
import { humanizeStatus } from "@/lib/financeLabels";
import api from "@/lib/api";
import { useSnackbar } from "notistack";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { rejectNegative } from "@/lib/numberBounds";

const moduleKey = "finance.invoices";
const basePath = "/finance/invoices";
const resourcePath = "/finance/invoices/";

type Vendor = { id: number; name: string; code?: string };
type TaxCode = {
  id: number;
  code: string;
  name: string;
  tax_type: string;
  rate_percent: string | number;
  is_active?: boolean;
};

export default function InvoiceForm({ mode }: { mode: FormMode }) {
  const params = useParams();
  const searchParams = useSearchParams();
  const id = mode === "create" ? undefined : String(params.id);
  const presetPo = searchParams.get("purchase_order") || "";
  const { canChange } = usePermissions();
  const { enqueueSnackbar } = useSnackbar();
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [taxCodes, setTaxCodes] = useState<TaxCode[]>([]);
  const [taxCodeId, setTaxCodeId] = useState("");
  const [paying, setPaying] = useState(false);
  const [banks, setBanks] = useState<{ id: number; name: string; account_no: string }[]>(
    []
  );
  const [poLabel, setPoLabel] = useState("");

  const empty = useMemo(
    () => ({
      vendor: "",
      purchase_order: presetPo,
      invoice_no: mode === "create" ? suggestDocNo("AP") : "",
      invoice_date: mode === "create" ? todayISO() : "",
      due_date: mode === "create" ? addDaysISO(todayISO(), 30) : "",
      amount: "0",
      wht_amount: "0",
      status: "draft",
      description: "",
      payment_ref: "",
      paid_amount: "",
      purchase_order_no: "",
      three_way_match: null as null | {
        ok?: boolean;
        status?: string;
        detail?: string;
      },
    }),
    [mode, presetPo]
  );

  const { form, setForm, loading, saving, save, reload, readOnly } = useEntityForm({
    resourcePath,
    entityLabel: "AP Invoice",
    basePath,
    mode,
    id,
    empty,
    mapLoaded: (row) => ({
      vendor: String(row.vendor ?? ""),
      purchase_order: row.purchase_order != null ? String(row.purchase_order) : "",
      invoice_no: String(row.invoice_no ?? ""),
      invoice_date: String(row.invoice_date ?? ""),
      due_date: String(row.due_date ?? ""),
      amount: String(row.amount ?? "0"),
      wht_amount: String(row.wht_amount ?? "0"),
      status: String(row.status ?? "draft"),
      description: String(row.description ?? ""),
      payment_ref: String(row.payment_ref ?? ""),
      paid_amount: String(row.paid_amount ?? ""),
      purchase_order_no: String(row.purchase_order_no ?? ""),
      three_way_match: (row.three_way_match as typeof empty.three_way_match) || null,
    }),
    mapPayload: (f) => ({
      vendor: f.vendor ? Number(f.vendor) : null,
      purchase_order: f.purchase_order ? Number(f.purchase_order) : null,
      invoice_no: f.invoice_no || null,
      invoice_date: f.invoice_date || null,
      due_date: f.due_date || null,
      amount: f.amount ? Number(f.amount) : 0,
      wht_amount: f.wht_amount ? Number(f.wht_amount) : 0,
      description: f.description,
    }),
  });

  useEffect(() => {
    if (mode !== "create" || !presetPo) return;
    api
      .get<Record<string, unknown>>(`/procurement/orders/${presetPo}/`)
      .then((r) => {
        const po = r.data;
        const terms = Number(po.payment_terms_days) || 30;
        const invDate = todayISO();
        setPoLabel(String(po.po_no || presetPo));
        setForm((prev) => ({
          ...prev,
          purchase_order: String(po.id ?? presetPo),
          vendor: po.vendor != null ? String(po.vendor) : prev.vendor,
          amount: String(po.amount ?? prev.amount),
          description: prev.description || `AP from PO ${po.po_no || ""}`,
          due_date: addDaysISO(invDate, terms),
          purchase_order_no: String(po.po_no ?? ""),
        }));
      })
      .catch(() => undefined);
  }, [mode, presetPo, setForm]);

  useEffect(() => {
    listResource<Vendor>("/finance/vendors/")
      .then(setVendors)
      .catch(() => undefined);
    listResource<TaxCode>("/finance/tax-codes/")
      .then((rows) =>
        setTaxCodes(rows.filter((t) => t.is_active !== false && t.tax_type === "wht"))
      )
      .catch(() => undefined);
    listResource<{ id: number; name: string; account_no: string }>("/finance/banks/")
      .then((rows) => setBanks(rows.filter(Boolean)))
      .catch(() => undefined);
  }, []);

  const status = String(form.status || "draft");
  const editable = status === "draft" || status === "rejected";
  const locked = mode !== "create" && !editable;
  const fieldsReadOnly = readOnly || locked;
  const amount = Number(form.amount) || 0;
  const wht = Number(form.wht_amount) || 0;
  const netPayable = amount - wht;

  const applyWhtRate = (codeId: string) => {
    setTaxCodeId(codeId);
    const tc = taxCodes.find((t) => String(t.id) === codeId);
    if (!tc) return;
    const rate = Number(tc.rate_percent) || 0;
    const computed = ((amount * rate) / 100).toFixed(2);
    setForm({ ...form, wht_amount: computed });
  };

  const recordPayment = async () => {
    if (!id) return;
    if (!banks.length) {
      enqueueSnackbar("Add a bank account (with GL link) before recording payment", {
        variant: "warning",
      });
      return;
    }
    const bankChoices = banks
      .map((b, i) => `${i + 1}. ${b.name} (${b.account_no})`)
      .join("\n");
    const pick = window.prompt(
      `Select paying bank (enter number):\n${bankChoices}`,
      "1"
    );
    const idx = (Number(pick) || 1) - 1;
    const bank = banks[idx];
    if (!bank) {
      enqueueSnackbar("Invalid bank selection", { variant: "warning" });
      return;
    }
    const ref =
      window.prompt("Payment reference (cheque / FT / bank ref)", "") || "";
    setPaying(true);
    try {
      const { data } = await api.post(`${resourcePath}${id}/record-payment/`, {
        payment_ref: ref,
        paid_amount: netPayable,
        bank_account: bank.id,
      });
      enqueueSnackbar(
        data?.gl_journal_ref
          ? `Paid · GL ${data.gl_journal_ref} posted`
          : "Payment recorded",
        { variant: "success" }
      );
      await reload();
    } catch (e) {
      enqueueSnackbar(getApiErrorMessage(e, "Payment failed"), errorSnackbarOpts);
    } finally {
      setPaying(false);
    }
  };

  const title =
    mode === "create" ? "Record a bill" : mode === "edit" ? "Edit bill" : "Bill";

  const vendorLabel = (() => {
    const v = vendors.find((x) => String(x.id) === String(form.vendor));
    if (!v) return form.vendor ? `Vendor #${form.vendor}` : "—";
    return codeNameLabel(v.code, v.name, "—");
  })();

  const workflowBar =
    id ? (
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <WorkflowActions
          resourcePath={resourcePath}
          id={Number(id)}
          status={status}
          moduleKey={moduleKey}
          onDone={reload}
        />
        {canChange(moduleKey) &&
        (status === "approved" || status === "submitted") ? (
          <Button
            size="small"
            variant="contained"
            color="secondary"
            startIcon={<PaymentsIcon />}
            disabled={paying}
            onClick={recordPayment}
          >
            Record payment
          </Button>
        ) : null}
        {mode === "view" && canChange(moduleKey) && editable ? (
          <Button
            component={Link}
            href={`${basePath}/${id}/edit`}
            variant="contained"
            startIcon={<EditIcon />}
          >
            Edit
          </Button>
        ) : null}
      </Stack>
    ) : null;

  if (mode === "view") {
    return (
      <ModuleGate module={moduleKey}>
        <DetailPageShell
          eyebrow="Accounts payable"
          title={String(form.invoice_no || "Invoice")}
          subtitle={vendorLabel}
          backHref={basePath}
          status={humanizeStatus(status)}
          loading={loading}
          extraActions={workflowBar}
          metrics={[
            { label: "Gross amount", value: formatMoney(form.amount) },
            { label: "WHT deducted", value: formatMoney(form.wht_amount) },
            { label: "Net payable", value: formatMoney(netPayable) },
            { label: "Due date", value: formatDate(String(form.due_date)) },
          ]}
        >
          {status === "paid" ? (
            <Alert severity="success" sx={{ mb: 2 }}>
              Paid {form.paid_amount ? formatMoney(form.paid_amount) : ""}
              {form.payment_ref ? ` · Ref ${form.payment_ref}` : ""}
            </Alert>
          ) : null}
          <DetailSection title="Invoice details" defaultExpanded>
            <DetailGrid>
              <DetailItem label="Vendor invoice no." value={form.invoice_no} />
              <DetailItem label="Vendor" value={vendorLabel} />
              <DetailItem
                label="Purchase order"
                value={
                  form.purchase_order_no || form.purchase_order
                    ? String(form.purchase_order_no || `PO #${form.purchase_order}`)
                    : "—"
                }
              />
              <DetailItem
                label="Invoice date"
                value={formatDate(String(form.invoice_date))}
              />
              <DetailItem label="Due date" value={formatDate(String(form.due_date))} />
            </DetailGrid>
          </DetailSection>
          <DetailSection title="Notes" defaultExpanded={false}>
            <DetailItem label="Description" value={form.description || "—"} fullWidth />
          </DetailSection>
        </DetailPageShell>
      </ModuleGate>
    );
  }

  return (
    <ModuleGate module={moduleKey}>
      <FormPageShell
        title={title}
        subtitle="Who you owe, what the bill says, and how much tax is held back."
        backHref={basePath}
        mode={fieldsReadOnly && mode !== "create" ? "view" : mode}
        loading={loading}
        saving={saving}
        onSubmit={save}
        submitLabel="Save and close"
        extraActions={workflowBar}
      >
        <Stack spacing={2}>
          {locked ? (
            <Alert severity="info">
              This bill is {humanizeStatus(status)}. It can be changed while it is a draft or has been sent back.
            </Alert>
          ) : null}
          {form.purchase_order && form.three_way_match ? (
            <Alert severity={form.three_way_match.ok ? "success" : "warning"}>
              3-way match: {form.three_way_match.detail}
            </Alert>
          ) : null}
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="body2" color="text.secondary">
              Status
            </Typography>
            <Chip size="small" label={humanizeStatus(status)} />
          </Stack>
          <RelationSelect
            label="Vendor"
            required
            value={form.vendor}
            disabled={fieldsReadOnly}
            relation={RELATIONS.vendor}
            onChange={(v) => setForm({ ...form, vendor: v, purchase_order: "" })}
          />
          <RelationSelect
            label="Purchase order (optional)"
            helperText="Link the order this bill pays, if you have one."
            value={String(form.purchase_order ?? "")}
            disabled={fieldsReadOnly}
            relation={RELATIONS.purchaseOrder}
            onChange={async (v) => {
              if (!v) {
                setForm({ ...form, purchase_order: "" });
                setPoLabel("");
                return;
              }
              try {
                const { data: po } = await api.get<Record<string, unknown>>(
                  `/procurement/orders/${v}/`
                );
                const terms = Number(po.payment_terms_days) || 30;
                const invDate = String(form.invoice_date || todayISO());
                setPoLabel(String(po.po_no || v));
                setForm({
                  ...form,
                  purchase_order: v,
                  vendor: po.vendor != null ? String(po.vendor) : form.vendor,
                  amount:
                    Number(form.amount) > 0
                      ? form.amount
                      : String(po.amount ?? form.amount),
                  description:
                    form.description || `AP from PO ${po.po_no || ""}`,
                  due_date: addDaysISO(invDate, terms),
                  purchase_order_no: String(po.po_no ?? ""),
                });
              } catch {
                setForm({ ...form, purchase_order: v });
              }
            }}
          />
          {poLabel || form.purchase_order_no ? (
            <Typography variant="caption" color="text.secondary">
              Linked PO: {poLabel || String(form.purchase_order_no)}
            </Typography>
          ) : null}
          <TextField
            label="Bill number"
            fullWidth
            required
            value={form.invoice_no}
            disabled={fieldsReadOnly}
            helperText="The number printed on their bill. Leave it blank and one is created for you."
            placeholder="AP-YYYY-#####"
            onChange={(e) => setForm({ ...form, invoice_no: e.target.value })}
          />
          <DateTextField
            label="Bill date"
            required
            value={form.invoice_date}
            disabled={fieldsReadOnly}
            onChange={(e) => {
              const invoice_date = e.target.value;
              const due =
                form.due_date ||
                (invoice_date ? addDaysISO(invoice_date, 30) : form.due_date);
              setForm({ ...form, invoice_date, due_date: due });
            }}
          />
          <DateTextField
            label="Due date"
            value={form.due_date}
            disabled={fieldsReadOnly}
            notBefore={form.invoice_date}
            helperText="When you need to pay it. Starts at 30 days after the bill date."
            onChange={(e) => setForm({ ...form, due_date: e.target.value })}
          />
          <TextField
            label="Bill amount"
            type="number"
            fullWidth
            value={form.amount}
            disabled={fieldsReadOnly}
            slotProps={{ htmlInput: { min: 0, step: "0.01" } }}
            onChange={(e) => {
              const next = rejectNegative(e.target.value, { min: 0 });
              if (next == null) return;
              const amt = Number(next) || 0;
              const tc = taxCodes.find((t) => String(t.id) === taxCodeId);
              const rate = tc ? Number(tc.rate_percent) || 0 : 0;
              setForm({
                ...form,
                amount: next,
                wht_amount: rate
                  ? ((amt * rate) / 100).toFixed(2)
                  : form.wht_amount,
              });
            }}
          />
          {!fieldsReadOnly && taxCodes.length > 0 ? (
            <TextField
              select
              label="Tax to withhold"
              fullWidth
              value={taxCodeId}
              helperText="The percent held back from this payment. You can type a different amount below."
              onChange={(e) => applyWhtRate(e.target.value)}
            >
              <MenuItem value="">— Type the tax amount —</MenuItem>
              {taxCodes.map((t) => (
                <MenuItem key={t.id} value={String(t.id)}>
                  {t.code} · {t.name} ({t.rate_percent}%)
                </MenuItem>
              ))}
            </TextField>
          ) : null}
          <TextField
            label="Tax held back"
            type="number"
            fullWidth
            value={form.wht_amount}
            disabled={fieldsReadOnly}
            slotProps={{ htmlInput: { min: 0, step: "0.01" } }}
            helperText="This amount stays with you to pay the tax office. The supplier receives the rest."
            onChange={(e) => {
              const next = rejectNegative(e.target.value, { min: 0 });
              if (next == null) return;
              setForm({ ...form, wht_amount: next });
            }}
          />
          <Alert severity="success" icon={false}>
            You will pay them: <strong>{formatMoney(netPayable)}</strong>
          </Alert>
          <TextField
            label="What the bill is for"
            multiline
            minRows={2}
            fullWidth
            value={form.description}
            disabled={fieldsReadOnly}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
        </Stack>
      </FormPageShell>
    </ModuleGate>
  );
}
