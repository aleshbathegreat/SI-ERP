"use client";

import { MenuItem, TextField } from "@mui/material";
import DateTextField, { DATE_ORDER, DATE_PLACEHOLDER } from "@/components/DateTextField";
import RelationSelect, {
  type RelationConfig,
} from "@/components/crud/RelationSelect";
import { numberBounds, rejectNegative, snapNumber, yearHint } from "@/lib/numberBounds";

export type FieldOption = { value: string; label: string };

export type FieldDef = {
  name: string;
  label: string;
  type?: "text" | "number" | "select" | "date" | "datetime" | "textarea" | "boolean" | "relation";
  required?: boolean;
  options?: FieldOption[];
  disabledOnEdit?: boolean;
  helperText?: string;
  fullWidth?: boolean;
  placeholder?: string;
  min?: number;
  max?: number;
  /** 1 stores a whole number. */
  step?: number;
  /** Mark field as auto-generated (read-only on create until user edits). */
  autoGenerate?: boolean;
  /** FK lookup with Add / Manage CRUD actions */
  relation?: RelationConfig;
  /** Show on detail view only; hidden (and not submitted) on create/edit forms. */
  formHidden?: boolean;
};

type Props = {
  fields: FieldDef[];
  values: Record<string, unknown>;
  onChange: (name: string, value: unknown) => void;
  readOnly?: boolean;
  mode?: "create" | "edit" | "view";
};

export default function EntityFormFields({
  fields,
  values,
  onChange,
  readOnly,
  mode = "create",
}: Props) {
  return (
    <>
      {fields.map((f) => {
        const disabled =
          !!readOnly || (mode === "edit" && !!f.disabledOnEdit);
        const raw = values[f.name];
        const type = f.relation ? "relation" : f.type || "text";

        if (type === "boolean") {
          const yes = raw === true || raw === "yes" || raw === "true";
          return (
            <TextField
              key={f.name}
              name={f.name}
              select
              label={f.label}
              required={f.required}
              value={yes ? "yes" : "no"}
              disabled={disabled}
              helperText={f.helperText}
              fullWidth
              onChange={(e) => onChange(f.name, e.target.value === "yes")}
            >
              <MenuItem value="yes">Yes</MenuItem>
              <MenuItem value="no">No</MenuItem>
            </TextField>
          );
        }

        if (type === "relation" && f.relation) {
          return (
            <RelationSelect
              key={f.name}
              label={f.label}
              required={f.required}
              value={raw == null ? "" : String(raw)}
              disabled={disabled}
              helperText={f.helperText}
              relation={f.relation}
              fallbackLabel={raw == null || raw === "" ? undefined : String(raw)}
              onChange={(v) => onChange(f.name, v === "" ? "" : Number(v) || v)}
            />
          );
        }

        if (type === "select") {
          const current = String(raw ?? "");
          const options = f.options || [];
          const shown =
            current && !options.some((option) => option.value === current)
              ? [{ value: current, label: current }, ...options]
              : options;
          return (
            <TextField
              key={f.name}
              name={f.name}
              select
              label={f.label}
              required={f.required}
              value={current}
              disabled={disabled}
              helperText={f.helperText}
              fullWidth
              onChange={(e) => onChange(f.name, e.target.value)}
            >
              <MenuItem value="">{f.required ? "Select" : "—"}</MenuItem>
              {shown.map((o) => (
                <MenuItem key={o.value || "blank"} value={o.value}>
                  {o.label}
                </MenuItem>
              ))}
            </TextField>
          );
        }

        if (type === "datetime") {
          return (
            <TextField
              key={f.name}
              name={f.name}
              label={f.label}
              required={f.required}
              type="datetime-local"
              value={toDatetimeLocal(raw)}
              disabled={disabled}
              helperText={f.helperText}
              fullWidth
              slotProps={{ inputLabel: { shrink: true } }}
              onChange={(e) => onChange(f.name, e.target.value)}
            />
          );
        }

        if (type === "date") {
          const earlier = DATE_ORDER.find((pair) => pair[1] === f.name);
          const notBefore = earlier ? String(values[earlier[0]] || "").slice(0, 10) : "";
          return (
            <DateTextField
              key={f.name}
              name={f.name}
              label={f.label}
              required={f.required}
              value={raw == null ? "" : String(raw)}
              disabled={disabled}
              helperText={f.helperText}
              showFormatHint={!f.helperText}
              notBefore={notBefore || undefined}
              onChange={(e) => onChange(f.name, e.target.value)}
            />
          );
        }

        const autoHint =
          f.autoGenerate && mode === "create" && !f.helperText
            ? "Auto-filled · you can edit before saving"
            : yearHint(f.name, f.helperText);
        const bounds = type === "number" ? numberBounds(f.name, f.min, f.max) : {};

        return (
          <TextField
            key={f.name}
            name={f.name}
            label={f.label}
            required={f.required && !f.autoGenerate}
            type={type === "number" ? "number" : "text"}
            placeholder={
              f.placeholder ||
              (f.autoGenerate ? "Auto-generated if left blank" : undefined)
            }
            multiline={type === "textarea"}
            minRows={type === "textarea" ? 3 : undefined}
            value={
              raw == null || raw === ""
                ? ""
                : type === "number" && f.step === 1 && Number.isFinite(Number(raw))
                  ? String(Math.round(Number(raw)))
                  : String(raw)
            }
            disabled={disabled}
            helperText={autoHint}
            fullWidth
            slotProps={
              type === "number"
                ? {
                    htmlInput: {
                      min: bounds.min,
                      max: bounds.max,
                      step: f.step ?? (bounds.max != null && bounds.max <= 2100 ? 1 : "any"),
                    },
                  }
                : undefined
            }
            onBlur={() => {
              if (type !== "number") return;
              let snapped = snapNumber(raw, bounds);
              if (f.step === 1 && typeof snapped === "number") snapped = Math.round(snapped);
              if (snapped !== "" && snapped !== Number(raw)) onChange(f.name, snapped);
            }}
            onChange={(e) => {
              if (type !== "number") {
                onChange(f.name, e.target.value);
                return;
              }
              const next = rejectNegative(e.target.value, bounds);
              if (next == null) return;
              if (next === "") {
                onChange(f.name, "");
                return;
              }
              const numeric = Number(next);
              const completeYear =
                (f.name === "year" || f.name === "fiscal_year" || f.name === "period_year") &&
                String(Math.trunc(Math.abs(numeric))).length >= 4;
              if (completeYear) {
                const snapped = snapNumber(numeric, bounds);
                onChange(f.name, snapped === "" ? "" : snapped);
                return;
              }
              onChange(f.name, f.step === 1 ? Math.trunc(numeric) : numeric);
            }}
          />
        );
      })}
    </>
  );
}

function toDatetimeLocal(raw: unknown): string {
  if (raw == null || raw === "") return "";
  const text = String(raw);
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(text)) return text;
  const parsed = new Date(text);
  if (Number.isNaN(parsed.getTime())) return "";
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${parsed.getFullYear()}-${pad(parsed.getMonth() + 1)}-${pad(parsed.getDate())}T${pad(parsed.getHours())}:${pad(parsed.getMinutes())}`;
}

export { DATE_PLACEHOLDER };
