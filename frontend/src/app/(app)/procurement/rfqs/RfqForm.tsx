"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  Box,
  Button,
  Chip,
  IconButton,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import DateTextField, { todayISO } from "@/components/DateTextField";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlined";
import EditIcon from "@mui/icons-material/Edit";
import { useSnackbar } from "notistack";
import FormPageShell from "@/components/crud/FormPageShell";
import { DetailSection } from "@/components/crud/DetailPageShell";
import RelationSelect, { RELATIONS } from "@/components/crud/RelationSelect";
import ModuleGate from "@/components/ModuleGate";
import { useEntityForm, type FormMode } from "@/hooks/useEntityForm";
import { usePermissions } from "@/hooks/usePermissions";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";

type Line = { item: string; description: string; qty: string };
type QuoteLine = { item: string; description: string; qty: string; unit_price: string };
type Quote = {
  id?: number;
  vendor: string;
  vendor_name?: string;
  quote_date: string;
  notes: string;
  is_winning?: boolean;
  lines: QuoteLine[];
  total?: string;
};

const emptyLine = (): Line => ({ item: "", description: "", qty: "1" });
const emptyQLine = (): QuoteLine => ({
  item: "",
  description: "",
  qty: "1",
  unit_price: "0",
});

const moduleKey = "procurement.rfq";
const basePath = "/procurement/rfqs";
const resourcePath = "/procurement/rfqs/";

export default function RfqForm({ mode }: { mode: FormMode }) {
  const params = useParams();
  const router = useRouter();
  const id = mode === "create" ? undefined : String(params.id);
  const { canChange } = usePermissions();
  const { enqueueSnackbar } = useSnackbar();
  const [busy, setBusy] = useState(false);
  const [newQuote, setNewQuote] = useState<Quote>({
    vendor: "",
    quote_date: todayISO(),
    notes: "",
    lines: [emptyQLine()],
  });

  const empty = useMemo(
    () => ({
      rfq_no: "",
      rfq_date: todayISO(),
      valid_until: todayISO(),
      warehouse: "",
      currency: "PKR",
      status: "draft",
      notes: "",
      lines: [emptyLine()] as Line[],
      quotes: [] as Quote[],
    }),
    []
  );

  const { form, setForm, loading, saving, save, reload, readOnly } = useEntityForm({
    resourcePath,
    entityLabel: "Vendor RFQ",
    basePath,
    mode,
    id,
    empty,
    mapLoaded: (row) => ({
      rfq_no: String(row.rfq_no ?? ""),
      rfq_date: String(row.rfq_date ?? empty.rfq_date),
      valid_until: String(row.valid_until ?? ""),
      warehouse: row.warehouse != null ? String(row.warehouse) : "",
      currency: String(row.currency ?? "PKR"),
      status: String(row.status ?? "draft"),
      notes: String(row.notes ?? ""),
      lines:
        Array.isArray(row.lines) && row.lines.length
          ? (row.lines as Record<string, unknown>[]).map((l) => ({
              item: l.item != null ? String(l.item) : "",
              description: String(l.description ?? ""),
              qty: String(l.qty ?? "1"),
            }))
          : [emptyLine()],
      quotes: Array.isArray(row.quotes) ? (row.quotes as Quote[]) : [],
    }),
    mapPayload: (f) => ({
      rfq_no: f.rfq_no || undefined,
      rfq_date: f.rfq_date,
      valid_until: f.valid_until || null,
      warehouse: f.warehouse ? Number(f.warehouse) : null,
      currency: f.currency || "PKR",
      notes: f.notes || "",
      lines: (f.lines as Line[]).map((l) => ({
        item: Number(l.item),
        description: l.description || "",
        qty: Number(l.qty) || 0,
      })),
    }),
  });

  const lines = (form.lines as Line[]) || [];
  const quotes = (form.quotes as Quote[]) || [];
  const locked = !["draft", "sent"].includes(String(form.status));
  const formReadOnly = readOnly || (mode === "edit" && locked);

  const setLine = (idx: number, patch: Partial<Line>) => {
    setForm({ ...form, lines: lines.map((l, i) => (i === idx ? { ...l, ...patch } : l)) });
  };

  const send = async () => {
    if (!id) return;
    setBusy(true);
    try {
      await api.post(`${resourcePath}${id}/send/`);
      enqueueSnackbar("RFQ sent", { variant: "success" });
      await reload();
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Send failed"), errorSnackbarOpts);
    } finally {
      setBusy(false);
    }
  };

  const award = async (quoteId: number) => {
    if (!id) return;
    setBusy(true);
    try {
      const { data } = await api.post<{ purchase_order_id: number; po_no: string }>(
        `${resourcePath}${id}/award/`,
        { quote_id: quoteId }
      );
      enqueueSnackbar(`Awarded → ${data.po_no}`, { variant: "success" });
      router.push(`/procurement/orders/${data.purchase_order_id}`);
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Award failed"), errorSnackbarOpts);
    } finally {
      setBusy(false);
    }
  };

  const addQuote = async () => {
    if (!id || !newQuote.vendor) return;
    setBusy(true);
    try {
      await api.post("/procurement/rfq-quotes/", {
        rfq: Number(id),
        vendor: Number(newQuote.vendor),
        quote_date: newQuote.quote_date,
        notes: newQuote.notes || "",
        lines: newQuote.lines.map((l) => ({
          item: Number(l.item),
          description: l.description || "",
          qty: Number(l.qty) || 0,
          unit_price: Number(l.unit_price) || 0,
        })),
      });
      enqueueSnackbar("Vendor quote added", { variant: "success" });
      setNewQuote({
        vendor: "",
        quote_date: todayISO(),
        notes: "",
        lines: [emptyQLine()],
      });
      await reload();
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Quote save failed"), errorSnackbarOpts);
    } finally {
      setBusy(false);
    }
  };

  return (
    <ModuleGate module={moduleKey}>
      <FormPageShell
        title={
          mode === "create" ? "New vendor RFQ" : mode === "edit" ? "Edit RFQ" : "Vendor RFQ"
        }
        subtitle="Collect vendor quotes and award a draft PO"
        backHref={basePath}
        mode={formReadOnly && mode === "edit" ? "view" : mode}
        loading={loading}
        saving={saving}
        onSubmit={save}
        maxWidth={960}
        extraActions={
          <>
            {mode === "view" && form.status === "draft" && canChange(moduleKey) ? (
              <Button variant="contained" disabled={busy} onClick={send}>
                Send RFQ
              </Button>
            ) : null}
            {mode === "view" &&
            canChange(moduleKey) &&
            id &&
            ["draft", "sent"].includes(String(form.status)) ? (
              <Button
                component={Link}
                href={`${basePath}/${id}/edit`}
                variant="outlined"
                startIcon={<EditIcon />}
              >
                Edit
              </Button>
            ) : null}
          </>
        }
      >
        <Stack spacing={2}>
          <Chip size="small" label={String(form.status)} variant="outlined" sx={{ alignSelf: "flex-start" }} />
          <DetailSection title="Header" defaultExpanded>
            <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" } }}>
              <TextField label="RFQ no" fullWidth value={form.rfq_no} disabled={formReadOnly} helperText="Blank = auto" onChange={(e) => setForm({ ...form, rfq_no: e.target.value })} />
              <DateTextField label="RFQ date" required value={form.rfq_date} disabled={formReadOnly} onChange={(e) => setForm({ ...form, rfq_date: e.target.value })} />
              <DateTextField label="Valid until" value={form.valid_until} disabled={formReadOnly} notBefore={form.rfq_date} onChange={(e) => setForm({ ...form, valid_until: e.target.value })} />
              <RelationSelect label="Warehouse" value={String(form.warehouse)} disabled={formReadOnly} relation={RELATIONS.warehouse} onChange={(v) => setForm({ ...form, warehouse: v })} />
              <RelationSelect label="Currency" required value={form.currency} disabled={formReadOnly} relation={RELATIONS.currency} onChange={(v) => setForm({ ...form, currency: v })} />
              <TextField label="Notes" multiline minRows={2} fullWidth value={form.notes} disabled={formReadOnly} onChange={(e) => setForm({ ...form, notes: e.target.value })} sx={{ gridColumn: { md: "1 / -1" } }} />
            </Box>
          </DetailSection>
          <DetailSection
            title="Requested lines"
            defaultExpanded
            action={
              !formReadOnly ? (
                <Button size="small" startIcon={<AddIcon />} onClick={() => setForm({ ...form, lines: [...lines, emptyLine()] })}>
                  Add line
                </Button>
              ) : null
            }
          >
            <Stack spacing={1.5}>
              {lines.map((line, idx) => (
                <Box key={idx} sx={{ display: "grid", gap: 1.5, gridTemplateColumns: { xs: "1fr", md: "2fr 1fr auto" }, p: 1.5, border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
                  <RelationSelect label="Item" required value={line.item} disabled={formReadOnly} relation={RELATIONS.item} onChange={(v) => setLine(idx, { item: v })} />
                  <TextField label="Qty" type="number" value={line.qty} disabled={formReadOnly} onChange={(e) => setLine(idx, { qty: e.target.value })} />
                  {!formReadOnly ? (
                    <IconButton disabled={lines.length <= 1} onClick={() => setForm({ ...form, lines: lines.filter((_, i) => i !== idx) })}>
                      <DeleteOutlineIcon />
                    </IconButton>
                  ) : (
                    <span />
                  )}
                  <TextField label="Description" value={line.description} disabled={formReadOnly} onChange={(e) => setLine(idx, { description: e.target.value })} sx={{ gridColumn: { md: "1 / -1" } }} />
                </Box>
              ))}
            </Stack>
          </DetailSection>

          {mode === "view" && id && ["draft", "sent"].includes(String(form.status)) ? (
            <DetailSection title="Add vendor quote" defaultExpanded>
              <Stack spacing={1.5}>
                <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" } }}>
                  <RelationSelect label="Vendor" required value={newQuote.vendor} relation={RELATIONS.vendor} onChange={(v) => setNewQuote({ ...newQuote, vendor: v })} />
                  <DateTextField label="Quote date" value={newQuote.quote_date} onChange={(e) => setNewQuote({ ...newQuote, quote_date: e.target.value })} />
                </Box>
                {newQuote.lines.map((ql, qi) => (
                  <Box key={qi} sx={{ display: "grid", gap: 1.5, gridTemplateColumns: { xs: "1fr", md: "2fr 1fr 1fr auto" } }}>
                    <RelationSelect label="Item" required value={ql.item} relation={RELATIONS.item} onChange={(v) => setNewQuote({ ...newQuote, lines: newQuote.lines.map((l, i) => (i === qi ? { ...l, item: v } : l)) })} />
                    <TextField label="Qty" type="number" value={ql.qty} onChange={(e) => setNewQuote({ ...newQuote, lines: newQuote.lines.map((l, i) => (i === qi ? { ...l, qty: e.target.value } : l)) })} />
                    <TextField label="Unit price" type="number" value={ql.unit_price} onChange={(e) => setNewQuote({ ...newQuote, lines: newQuote.lines.map((l, i) => (i === qi ? { ...l, unit_price: e.target.value } : l)) })} />
                    <IconButton onClick={() => setNewQuote({ ...newQuote, lines: [...newQuote.lines, emptyQLine()] })}>
                      <AddIcon />
                    </IconButton>
                  </Box>
                ))}
                <Button variant="contained" disabled={busy || !newQuote.vendor} onClick={addQuote}>
                  Save quote
                </Button>
              </Stack>
            </DetailSection>
          ) : null}

          {mode === "view" && quotes.length ? (
            <DetailSection title="Vendor quotes" defaultExpanded>
              <Stack spacing={2}>
                {quotes.map((q) => (
                  <Box key={q.id} sx={{ p: 1.5, border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
                    <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                      <Typography fontWeight={600}>{q.vendor_name || `Vendor ${q.vendor}`}</Typography>
                      {q.is_winning ? <Chip size="small" color="success" label="winning" /> : null}
                      <Typography variant="body2" color="text.secondary">
                        Total {q.total ?? "—"}
                      </Typography>
                      {canChange(moduleKey) &&
                      ["draft", "sent"].includes(String(form.status)) &&
                      q.id ? (
                        <Button size="small" variant="contained" disabled={busy} onClick={() => award(q.id!)}>
                          Award
                        </Button>
                      ) : null}
                    </Stack>
                    {(q.lines || []).map((l, i) => (
                      <Typography key={i} variant="body2">
                        {l.item} · qty {l.qty} @ {l.unit_price}
                      </Typography>
                    ))}
                  </Box>
                ))}
              </Stack>
            </DetailSection>
          ) : null}
        </Stack>
      </FormPageShell>
    </ModuleGate>
  );
}
