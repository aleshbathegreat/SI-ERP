"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Alert,
  Button,
  Chip,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import PaymentsIcon from "@mui/icons-material/Payments";
import FormPageShell from "@/components/crud/FormPageShell";
import { DetailSection } from "@/components/crud/DetailPageShell";
import DateTextField, { todayISO } from "@/components/DateTextField";
import ModuleGate from "@/components/ModuleGate";
import WorkflowActions from "@/components/WorkflowActions";
import { useEntityForm, type FormMode } from "@/hooks/useEntityForm";
import { usePermissions } from "@/hooks/usePermissions";
import { useParams, useSearchParams } from "next/navigation";
import { listResource } from "@/lib/crudApi";
import RelationSelect, { RELATIONS } from "@/components/crud/RelationSelect";
import { suggestDocNo, addDaysISO } from "@/lib/docNumbers";
import { formatMoney } from "@/lib/format";
import api from "@/lib/api";
import { useSnackbar } from "notistack";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";

const moduleKey = "sales.invoices";
const basePath = "/sales/invoices";
const resourcePath = "/sales/invoices/";

export default function ArInvoiceForm({ mode }: { mode: FormMode }) {
  const params = useParams();
  const searchParams = useSearchParams();
  const id = mode === "create" ? undefined : String(params.id);
  const presetSo = searchParams.get("sales_order") || "";
  const { canChange } = usePermissions();
  const { enqueueSnackbar } = useSnackbar();
  const [paying, setPaying] = useState(false);
  const [banks, setBanks] = useState<{ id: number; name: string; account_no: string }[]>([]);

  const empty = useMemo(
    () => ({
      customer: "",
      sales_order: presetSo,
      invoice_no: mode === "create" ? suggestDocNo("AR") : "",
      invoice_date: mode === "create" ? todayISO() : "",
      due_date: mode === "create" ? addDaysISO(todayISO(), 30) : "",
      amount: "0",
      tax_amount: "0",
      status: "draft",
      description: "",
      payment_ref: "",
      paid_amount: "",
      sales_order_no: "",
    }),
    [mode, presetSo]
  );

  const { form, setForm, loading, saving, save, reload, readOnly } = useEntityForm({
    resourcePath,
    entityLabel: "AR Invoice",
    basePath,
    mode,
    id,
    empty,
    mapLoaded: (row) => ({
      customer: String(row.customer ?? ""),
      sales_order: row.sales_order != null ? String(row.sales_order) : "",
      invoice_no: String(row.invoice_no ?? ""),
      invoice_date: String(row.invoice_date ?? ""),
      due_date: String(row.due_date ?? ""),
      amount: String(row.amount ?? "0"),
      tax_amount: String(row.tax_amount ?? "0"),
      status: String(row.status ?? "draft"),
      description: String(row.description ?? ""),
      payment_ref: String(row.payment_ref ?? ""),
      paid_amount: String(row.paid_amount ?? ""),
      sales_order_no: String(row.sales_order_no ?? ""),
    }),
    mapPayload: (f) => ({
      customer: f.customer ? Number(f.customer) : null,
      sales_order: f.sales_order ? Number(f.sales_order) : null,
      invoice_no: f.invoice_no || null,
      invoice_date: f.invoice_date || null,
      due_date: f.due_date || null,
      amount: f.amount ? Number(f.amount) : 0,
      tax_amount: f.tax_amount ? Number(f.tax_amount) : 0,
      description: f.description,
    }),
  });

  useEffect(() => {
    listResource<{ id: number; name: string; account_no: string }>("/finance/banks/")
      .then((rows) => setBanks(rows.filter(Boolean)))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (mode !== "create" || !presetSo) return;
    api
      .get<Record<string, unknown>>(`/sales/orders/${presetSo}/`)
      .then((r) => {
        const so = r.data;
        const terms = Number(so.payment_terms_days) || 30;
        setForm((prev) => ({
          ...prev,
          sales_order: String(so.id ?? presetSo),
          customer: so.customer != null ? String(so.customer) : prev.customer,
          amount: String(so.amount ?? prev.amount),
          tax_amount: String(so.tax_amount ?? prev.tax_amount),
          description: prev.description || `AR from SO ${so.order_no || ""}`,
          due_date: addDaysISO(todayISO(), terms),
          sales_order_no: String(so.order_no ?? ""),
        }));
      })
      .catch(() => undefined);
  }, [mode, presetSo, setForm]);

  const status = String(form.status || "draft");
  const editable = status === "draft" || status === "rejected";
  const locked = mode !== "create" && !editable;
  const fieldsReadOnly = readOnly || locked;
  const net = (Number(form.amount) || 0) + (Number(form.tax_amount) || 0);

  const recordPayment = async () => {
    if (!id) return;
    if (!banks.length) {
      enqueueSnackbar("Add a bank account before recording receipt", { variant: "warning" });
      return;
    }
    const pick = window.prompt(
      banks.map((b, i) => `${i + 1}. ${b.name} (${b.account_no})`).join("\n"),
      "1"
    );
    const bank = banks[(Number(pick) || 1) - 1];
    if (!bank) return;
    const ref = window.prompt("Payment reference", "") || "";
    setPaying(true);
    try {
      const { data } = await api.post(`${resourcePath}${id}/record-payment/`, {
        payment_ref: ref,
        paid_amount: net,
        bank_account: bank.id,
      });
      enqueueSnackbar(
        data?.gl_journal_ref ? `Received · GL ${data.gl_journal_ref}` : "Receipt recorded",
        { variant: "success" }
      );
      await reload();
    } catch (e) {
      enqueueSnackbar(getApiErrorMessage(e, "Receipt failed"), errorSnackbarOpts);
    } finally {
      setPaying(false);
    }
  };

  return (
    <ModuleGate module={moduleKey}>
      <FormPageShell
        title={mode === "create" ? "New AR invoice" : mode === "edit" ? "Edit AR invoice" : "AR invoice"}
        subtitle="Customer bill · LoA · bank receipt"
        backHref={basePath}
        mode={fieldsReadOnly && mode !== "create" ? "view" : mode}
        loading={loading}
        saving={saving}
        onSubmit={save}
        submitLabel="Save and close"
        extraActions={
          id ? (
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              <WorkflowActions resourcePath={resourcePath} id={Number(id)} status={status} moduleKey={moduleKey} onDone={reload} />
              {canChange(moduleKey) && ["approved", "submitted"].includes(status) ? (
                <Button size="small" variant="contained" color="secondary" startIcon={<PaymentsIcon />} disabled={paying} onClick={recordPayment}>
                  Record receipt
                </Button>
              ) : null}
              {mode === "view" && canChange(moduleKey) && editable ? (
                <Button component={Link} href={`${basePath}/${id}/edit`} variant="contained" startIcon={<EditIcon />}>
                  Edit
                </Button>
              ) : null}
            </Stack>
          ) : null
        }
      >
        <Stack spacing={2}>
          {locked ? (
            <Alert severity="info">Status is {status} — use LoA / receipt actions.</Alert>
          ) : null}
          <Chip size="small" label={status} />
          <DetailSection title="Header" defaultExpanded>
            <Stack spacing={2}>
              <RelationSelect label="Customer" required value={String(form.customer)} disabled={fieldsReadOnly} relation={RELATIONS.customer} onChange={(v) => setForm({ ...form, customer: v })} />
              {form.sales_order || form.sales_order_no ? (
                <Typography variant="body2" color="text.secondary">
                  Linked SO: {String(form.sales_order_no || form.sales_order)}
                </Typography>
              ) : null}
              <TextField label="Invoice no" fullWidth value={form.invoice_no} disabled={fieldsReadOnly} helperText="Blank = auto AR-YYYY-#####" onChange={(e) => setForm({ ...form, invoice_no: e.target.value })} />
              <DateTextField label="Invoice date" required value={form.invoice_date} disabled={fieldsReadOnly} onChange={(e) => setForm({ ...form, invoice_date: e.target.value })} />
              <DateTextField label="Due date" value={form.due_date} disabled={fieldsReadOnly} notBefore={form.invoice_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} />
              <TextField label="Amount" type="number" fullWidth value={form.amount} disabled={fieldsReadOnly} onChange={(e) => setForm({ ...form, amount: e.target.value })} />
              <TextField label="Tax" type="number" fullWidth value={form.tax_amount} disabled={fieldsReadOnly} onChange={(e) => setForm({ ...form, tax_amount: e.target.value })} />
              <Alert severity="success" icon={false}>
                Net receivable: <strong>{formatMoney(net)}</strong>
              </Alert>
              <TextField label="Description" multiline minRows={2} fullWidth value={form.description} disabled={fieldsReadOnly} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </Stack>
          </DetailSection>
        </Stack>
      </FormPageShell>
    </ModuleGate>
  );
}
