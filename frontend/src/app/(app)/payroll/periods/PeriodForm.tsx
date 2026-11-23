"use client";

import { useMemo } from "react";
import Link from "next/link";
import { useSelector } from "react-redux";
import { Button, MenuItem, TextField } from "@mui/material";
import DateTextField, { todayISO } from "@/components/DateTextField";
import EditIcon from "@mui/icons-material/Edit";
import FormPageShell from "@/components/crud/FormPageShell";
import ModuleGate from "@/components/ModuleGate";
import { useEntityForm, type FormMode } from "@/hooks/useEntityForm";
import { usePermissions } from "@/hooks/usePermissions";
import RelationSelect, { RELATIONS } from "@/components/crud/RelationSelect";
import { normalizeCurrency } from "@/lib/currencies";
import { numberBounds, rejectNegative, snapNumber } from "@/lib/numberBounds";
import type { RootState } from "@/store";

const BASE = "/payroll/periods";
const MODULE = "payroll.periods";
const API = "/payroll/periods/";

const emptyBase = {
  name: "",
  year: String(new Date().getFullYear()),
  month: String(new Date().getMonth() + 1),
  status: "open",
  pay_date: todayISO(),
  currency: "PKR",
  notes: "",
};

function createDefaults(currency: string) {
  const y = new Date().getFullYear();
  const m = new Date().getMonth() + 1;
  return {
    ...emptyBase,
    year: String(y),
    month: String(m),
    currency: normalizeCurrency(currency),
    name: new Date(y, m - 1, 1).toLocaleString("en", { month: "long", year: "numeric" }),
  };
}

export default function PeriodForm({ mode, id }: { mode: FormMode; id?: string }) {
  const { canChange } = usePermissions();
  const orgCurrency = useSelector((s: RootState) => s.auth.organization?.currency);
  const empty = useMemo(
    () => (mode === "create" ? createDefaults(orgCurrency || "PKR") : emptyBase),
    [mode, orgCurrency]
  );

  const { form, setForm, loading, saving, save, readOnly } = useEntityForm({
    resourcePath: API,
    entityLabel: "Payroll period",
    basePath: "/payroll",
    mode,
    id,
    empty,
    mapLoaded: (row) => ({
      name: String(row.name ?? ""),
      year: String(row.year ?? ""),
      month: String(row.month ?? ""),
      status: String(row.status ?? "open"),
      pay_date: String(row.pay_date ?? ""),
      currency: normalizeCurrency(String(row.currency ?? orgCurrency ?? "PKR")),
      notes: String(row.notes ?? ""),
    }),
    mapPayload: (f) => ({
      name: f.name,
      year: Number(f.year),
      month: Number(f.month),
      status: f.status,
      pay_date: f.pay_date || null,
      currency: normalizeCurrency(f.currency),
      notes: f.notes,
    }),
  });

  const title =
    mode === "create" ? "Add period" : mode === "edit" ? "Edit period" : "View period";

  return (
    <ModuleGate module={MODULE}>
      <FormPageShell
        title={title}
        subtitle="Monthly payroll run with LoA workflow"
        backHref="/payroll"
        backLabel="Back to payroll"
        mode={mode}
        loading={loading}
        saving={saving}
        onSubmit={save}
        maxWidth={720}
        extraActions={
          mode === "view" && canChange(MODULE) && id ? (
            <Button
              component={Link}
              href={`${BASE}/${id}/edit`}
              variant="contained"
              startIcon={<EditIcon />}
            >
              Edit
            </Button>
          ) : null
        }
      >
        <TextField
          label="Name"
          required
          fullWidth
          value={form.name}
          disabled={readOnly}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
        />
        <TextField
          label="Year"
          type="number"
          required
          fullWidth
          value={form.year}
          disabled={readOnly}
          helperText="2000–2100"
          inputProps={numberBounds("year")}
          onBlur={() => {
            const snapped = snapNumber(form.year, numberBounds("year"));
            if (snapped !== "" && String(snapped) !== String(form.year)) {
              setForm({ ...form, year: String(snapped) });
            }
          }}
          onChange={(e) => {
            const next = rejectNegative(e.target.value, numberBounds("year"));
            if (next == null) return;
            setForm({ ...form, year: next });
          }}
        />
        <TextField
          label="Month"
          type="number"
          required
          fullWidth
          value={form.month}
          disabled={readOnly}
          helperText="1–12"
          inputProps={numberBounds("month")}
          onBlur={() => {
            const snapped = snapNumber(form.month, numberBounds("month"));
            if (snapped !== "" && String(snapped) !== String(form.month)) {
              setForm({ ...form, month: String(snapped) });
            }
          }}
          onChange={(e) => {
            const next = rejectNegative(e.target.value, numberBounds("month"));
            if (next == null) return;
            setForm({ ...form, month: next });
          }}
        />
        <TextField
          label="Pay date"
          type="date"
          placeholder="YYYY-MM-DD"
          helperText="Pick a date - YYYY-MM-DD"
          fullWidth
          InputLabelProps={{ shrink: true }}
          value={form.pay_date}
          disabled={readOnly}
          onChange={(e) => setForm({ ...form, pay_date: e.target.value })}
        />
        <RelationSelect
          label="Currency"
          required
          helperText="Defaults from the company currency"
          value={form.currency}
          disabled={readOnly}
          relation={RELATIONS.currency}
          onChange={(v) => setForm({ ...form, currency: v })}
        />
        <TextField
          select
          label="Status"
          fullWidth
          value={form.status}
          disabled={readOnly}
          onChange={(e) => setForm({ ...form, status: e.target.value })}
        >
          {["open", "processing", "approved", "paid", "closed"].map((s) => (
            <MenuItem key={s} value={s}>
              {s}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          label="Notes"
          multiline
          minRows={2}
          fullWidth
          value={form.notes}
          disabled={readOnly}
          onChange={(e) => setForm({ ...form, notes: e.target.value })}
        />
      </FormPageShell>
    </ModuleGate>
  );
}
