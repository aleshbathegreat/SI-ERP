"use client";

import { useMemo } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  Box,
  Button,
  Chip,
  IconButton,
  Stack,
  TextField,
} from "@mui/material";
import DateTextField, { todayISO } from "@/components/DateTextField";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlined";
import EditIcon from "@mui/icons-material/Edit";
import FormPageShell from "@/components/crud/FormPageShell";
import { DetailSection } from "@/components/crud/DetailPageShell";
import RelationSelect, { RELATIONS } from "@/components/crud/RelationSelect";
import ModuleGate from "@/components/ModuleGate";
import { useEntityForm, type FormMode } from "@/hooks/useEntityForm";
import { usePermissions } from "@/hooks/usePermissions";

type ItemRow = { item: string; unit_price: string; valid_from: string; valid_until: string };
const emptyItem = (): ItemRow => ({
  item: "",
  unit_price: "0",
  valid_from: todayISO(),
  valid_until: todayISO(),
});
const moduleKey = "sales.pricing";
const basePath = "/sales/pricing";
const resourcePath = "/sales/pricing/";

export default function PriceListForm({ mode }: { mode: FormMode }) {
  const params = useParams();
  const id = mode === "create" ? undefined : String(params.id);
  const { canChange } = usePermissions();

  const empty = useMemo(
    () => ({
      code: "",
      name: "",
      customer: "",
      currency: "PKR",
      valid_from: todayISO(),
      valid_until: "",
      is_active: true,
      notes: "",
      items: [emptyItem()] as ItemRow[],
    }),
    []
  );

  const { form, setForm, loading, saving, save, readOnly } = useEntityForm({
    resourcePath,
    entityLabel: "Price list",
    basePath,
    mode,
    id,
    empty,
    mapLoaded: (row) => ({
      code: String(row.code ?? ""),
      name: String(row.name ?? ""),
      customer: row.customer != null ? String(row.customer) : "",
      currency: String(row.currency ?? "PKR"),
      valid_from: String(row.valid_from ?? ""),
      valid_until: String(row.valid_until ?? ""),
      is_active: Boolean(row.is_active ?? true),
      notes: String(row.notes ?? ""),
      items:
        Array.isArray(row.items) && row.items.length
          ? (row.items as Record<string, unknown>[]).map((l) => ({
              item: l.item != null ? String(l.item) : "",
              unit_price: String(l.unit_price ?? "0"),
              valid_from: String(l.valid_from ?? ""),
              valid_until: String(l.valid_until ?? ""),
            }))
          : [emptyItem()],
    }),
    mapPayload: (f) => ({
      code: f.code || undefined,
      name: f.name,
      customer: f.customer ? Number(f.customer) : null,
      currency: f.currency || "PKR",
      valid_from: f.valid_from || null,
      valid_until: f.valid_until || null,
      is_active: Boolean(f.is_active),
      notes: f.notes || "",
      items: (f.items as ItemRow[]).map((l) => ({
        item: Number(l.item),
        unit_price: Number(l.unit_price) || 0,
        valid_from: l.valid_from || null,
        valid_until: l.valid_until || null,
      })),
    }),
  });

  const items = (form.items as ItemRow[]) || [];
  const formReadOnly = readOnly;
  const setItem = (idx: number, patch: Partial<ItemRow>) => {
    setForm({ ...form, items: items.map((l, i) => (i === idx ? { ...l, ...patch } : l)) });
  };

  return (
    <ModuleGate module={moduleKey}>
      <FormPageShell
        title={mode === "create" ? "New price list" : mode === "edit" ? "Edit price list" : "Price list"}
        subtitle="Item unit prices with optional customer / validity"
        backHref={basePath}
        mode={mode}
        loading={loading}
        saving={saving}
        onSubmit={save}
        maxWidth={960}
        extraActions={
          mode === "view" && canChange(moduleKey) && id ? (
            <Button component={Link} href={`${basePath}/${id}/edit`} variant="contained" startIcon={<EditIcon />}>
              Edit
            </Button>
          ) : null
        }
      >
        <Stack spacing={2}>
          <Chip size="small" label={form.is_active ? "active" : "inactive"} variant="outlined" sx={{ alignSelf: "flex-start" }} />
          <DetailSection title="Header" defaultExpanded>
            <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" } }}>
              <TextField label="Code" fullWidth value={form.code} disabled={formReadOnly} helperText="Blank = auto" onChange={(e) => setForm({ ...form, code: e.target.value })} />
              <TextField label="Name" required fullWidth value={form.name} disabled={formReadOnly} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              <RelationSelect label="Customer (optional)" value={String(form.customer)} disabled={formReadOnly} relation={RELATIONS.customer} onChange={(v) => setForm({ ...form, customer: v })} />
              <RelationSelect label="Currency" required value={form.currency} disabled={formReadOnly} relation={RELATIONS.currency} onChange={(v) => setForm({ ...form, currency: v })} />
              <DateTextField label="Valid from" value={form.valid_from} disabled={formReadOnly} onChange={(e) => setForm({ ...form, valid_from: e.target.value })} />
              <DateTextField label="Valid until" value={form.valid_until} disabled={formReadOnly} notBefore={form.valid_from} onChange={(e) => setForm({ ...form, valid_until: e.target.value })} />
              <TextField label="Notes" multiline minRows={2} fullWidth value={form.notes} disabled={formReadOnly} onChange={(e) => setForm({ ...form, notes: e.target.value })} sx={{ gridColumn: { md: "1 / -1" } }} />
            </Box>
          </DetailSection>
          <DetailSection
            title="Items"
            defaultExpanded
            action={
              !formReadOnly ? (
                <Button size="small" startIcon={<AddIcon />} onClick={() => setForm({ ...form, items: [...items, emptyItem()] })}>
                  Add item
                </Button>
              ) : null
            }
          >
            <Stack spacing={1.5}>
              {items.map((row, idx) => (
                <Box key={idx} sx={{ display: "grid", gap: 1.5, gridTemplateColumns: { xs: "1fr", md: "2fr 1fr 1fr 1fr auto" }, p: 1.5, border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
                  <RelationSelect label="Item" required value={row.item} disabled={formReadOnly} relation={RELATIONS.item} onChange={(v) => setItem(idx, { item: v })} />
                  <TextField label="Unit price" type="number" value={row.unit_price} disabled={formReadOnly} onChange={(e) => setItem(idx, { unit_price: e.target.value })} />
                  <DateTextField label="From" value={row.valid_from} disabled={formReadOnly} onChange={(e) => setItem(idx, { valid_from: e.target.value })} />
                  <DateTextField label="Until" value={row.valid_until} disabled={formReadOnly} notBefore={row.valid_from} onChange={(e) => setItem(idx, { valid_until: e.target.value })} />
                  {!formReadOnly ? (
                    <IconButton disabled={items.length <= 1} onClick={() => setForm({ ...form, items: items.filter((_, i) => i !== idx) })}>
                      <DeleteOutlineIcon />
                    </IconButton>
                  ) : (
                    <span />
                  )}
                </Box>
              ))}
            </Stack>
          </DetailSection>
        </Stack>
      </FormPageShell>
    </ModuleGate>
  );
}
