"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Box,
  Button,
  IconButton,
  MenuItem,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import RefreshIcon from "@mui/icons-material/Refresh";
import { useSnackbar } from "notistack";
import FormDialog from "@/components/crud/FormDialog";
import { todayISO } from "@/components/DateTextField";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { codeNameLabel, distinctLabel, sameToken } from "@/lib/optionLabel";
import { numberBounds, rejectNegative, snapNumber, yearHint } from "@/lib/numberBounds";

export type RelationQuickField = {
  name: string;
  label: string;
  required?: boolean;
  type?: "text" | "number" | "date" | "select";
  defaultValue?: string | number | boolean;
  options?: { value: string; label: string }[];
};

export type RelationConfig = {
  /** API list endpoint e.g. /finance/vendors/ */
  apiPath: string;
  /** Route for full CRUD list e.g. /finance/vendors */
  listPath: string;
  entityLabel: string;
  /** Build option label from row */
  getOptionLabel: (row: Record<string, unknown>) => string;
  /** Value stored on the form field (default: row.id) */
  getOptionValue?: (row: Record<string, unknown>) => string;
  /** Quick-create fields (opens dialog) */
  createFields?: RelationQuickField[];
  /** Extra payload defaults on create */
  createDefaults?: Record<string, unknown>;
  allowClear?: boolean;
  clearLabel?: string;
};

type Props = {
  label: string;
  value: string | number | null | undefined;
  onChange: (value: string) => void;
  relation: RelationConfig;
  required?: boolean;
  disabled?: boolean;
  helperText?: string;
  fullWidth?: boolean;
  size?: "small" | "medium";
  /** Narrow the list. If nothing matches, the full list is shown. */
  rowFilter?: (row: Record<string, unknown>) => boolean;
  /** Shown when the saved id is missing from the active list (for example a retired class). */
  fallbackLabel?: string;
};

export default function RelationSelect({
  label,
  value,
  onChange,
  relation,
  required,
  disabled,
  helperText,
  fullWidth = true,
  size,
  rowFilter,
  fallbackLabel,
}: Props) {
  const { enqueueSnackbar } = useSnackbar();
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState<Record<string, unknown>>({});

  const selectedId = value == null || value === "" || value === 0 ? "" : String(value);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data: Record<string, unknown>[] = [];
      let path: string | null = relation.apiPath;
      for (let page = 0; path && page < 15; page += 1) {
        const { data: payload } = await api.get<
          Record<string, unknown>[] | { results?: Record<string, unknown>[]; next?: string | null }
        >(path);
        if (Array.isArray(payload)) {
          data.push(...payload);
          break;
        }
        data.push(...(payload.results || []));
        path = payload.next || null;
      }
      const optionValue = (row: Record<string, unknown>) =>
        relation.getOptionValue ? relation.getOptionValue(row) : String(row.id ?? "");
      const matchesSelected = (row: Record<string, unknown>) =>
        Boolean(selectedId) &&
        (String(row.id ?? "") === selectedId || optionValue(row) === selectedId);
      const kept = data.filter((r) => {
        if (!r) return false;
        if (matchesSelected(r)) return true;
        if (Object.prototype.hasOwnProperty.call(r, "is_active")) {
          return r.is_active !== false;
        }
        return true;
      });
      if (selectedId && /^\d+$/.test(selectedId) && !kept.some((r) => matchesSelected(r))) {
        const base = relation.apiPath.endsWith("/") ? relation.apiPath : `${relation.apiPath}/`;
        try {
          const { data: one } = await api.get<Record<string, unknown>>(`${base}${selectedId}/`);
          if (one && typeof one === "object") kept.unshift(one);
        } catch {
          /* selected row is gone; the field stays empty */
        }
      }
      setRows(kept);
    } catch {
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [relation.apiPath, selectedId]);

  useEffect(() => {
    load().catch(() => undefined);
  }, [load]);

  const noun = (relation.entityLabel || "record").toLowerCase();

  const openCreate = () => {
    const init: Record<string, unknown> = { ...(relation.createDefaults || {}) };
    for (const f of relation.createFields || []) {
      if (init[f.name] !== undefined) continue;
      if (f.defaultValue !== undefined) {
        init[f.name] = f.defaultValue;
      } else if (f.type === "date") {
        init[f.name] = todayISO();
      } else if (f.type === "number") {
        init[f.name] = 0;
      } else {
        init[f.name] = "";
      }
    }
    setDraft(init);
    setDialogOpen(true);
  };

  const submitCreate = async () => {
    const fields = relation.createFields || [];
    for (const f of fields) {
      if (f.required && (draft[f.name] === "" || draft[f.name] == null)) {
        enqueueSnackbar(`${f.label} is required`, { variant: "warning" });
        return;
      }
    }
    setSaving(true);
    try {
      const payload: Record<string, unknown> = { ...draft };
      for (const f of fields) {
        if (f.type === "date" && payload[f.name] === "") payload[f.name] = null;
        if (f.type === "number" && payload[f.name] === "") payload[f.name] = null;
      }
      const { data } = await api.post(relation.apiPath, payload);
      enqueueSnackbar(`${relation.entityLabel} created`, { variant: "success" });
      setDialogOpen(false);
      await load();
      if (data && typeof data === "object") {
        const row = data as Record<string, unknown>;
        const v = relation.getOptionValue
          ? relation.getOptionValue(row)
          : row.id != null
            ? String(row.id)
            : "";
        if (v) onChange(v);
      }
    } catch (e) {
      enqueueSnackbar(
        getApiErrorMessage(e, `Could not create ${noun}`),
        errorSnackbarOpts
      );
    } finally {
      setSaving(false);
    }
  };

  const strValue = value == null || value === 0 ? "" : String(value);
  const canQuickCreate = (relation.createFields || []).length > 0 && !disabled;
  const optionValue = (row: Record<string, unknown>) =>
    relation.getOptionValue ? relation.getOptionValue(row) : String(row.id ?? "");
  const visibleRows = useMemo(() => {
    const matches = (row: Record<string, unknown>) =>
      optionValue(row) === strValue || String(row.id ?? "") === strValue;
    if (!rowFilter) return rows;
    const picked = rows.filter(rowFilter);
    const base = picked.length ? picked : rows;
    if (!strValue || base.some(matches)) return base;
    const current = rows.find(matches);
    return current ? [current, ...base] : base;
  }, [rows, rowFilter, strValue, relation]);

  const hint = useMemo(() => {
    if (helperText) return helperText;
    if (!rows.length && !loading) {
      return `No ${noun}s yet — use Add`;
    }
    return undefined;
  }, [helperText, rows.length, loading, noun]);

  return (
    <Box>
      <Stack direction="row" spacing={1} alignItems="flex-start">
        <TextField
          select
          label={label}
          required={required}
          fullWidth={fullWidth}
          size={size}
          value={strValue}
          disabled={disabled || loading}
          helperText={hint}
          onChange={(e) => onChange(e.target.value)}
          sx={{ flex: 1 }}
        >
          {relation.allowClear ? (
            <MenuItem value="">{relation.clearLabel || "— None —"}</MenuItem>
          ) : null}
          {strValue &&
          fallbackLabel &&
          !visibleRows.some((r) => {
            const optVal = relation.getOptionValue
              ? relation.getOptionValue(r)
              : String(r.id ?? "");
            return optVal === strValue;
          }) ? (
            <MenuItem value={strValue}>{fallbackLabel}</MenuItem>
          ) : null}
          {visibleRows.map((r) => {
            const optVal = relation.getOptionValue
              ? relation.getOptionValue(r)
              : String(r.id ?? "");
            const optLabel = relation.getOptionLabel
              ? relation.getOptionLabel(r)
              : String(r.id ?? "");
            return (
              <MenuItem key={optVal || String(r.id)} value={optVal}>
                {optLabel}
              </MenuItem>
            );
          })}
        </TextField>
        <Stack direction="row" spacing={0.5} sx={{ pt: 0.5 }}>
          {canQuickCreate ? (
            <Tooltip title={`Add ${noun}`}>
              <IconButton
                color="primary"
                onClick={openCreate}
                aria-label={`Add ${relation.entityLabel}`}
              >
                <AddIcon />
              </IconButton>
            </Tooltip>
          ) : null}
          <Tooltip title="Refresh list">
            <IconButton onClick={() => load()} disabled={loading} aria-label="Refresh">
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title={`Manage ${noun}s`}>
            <IconButton
              component={Link}
              href={relation.listPath || "#"}
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Manage"
            >
              <OpenInNewIcon />
            </IconButton>
          </Tooltip>
        </Stack>
      </Stack>

      <FormDialog
        open={dialogOpen}
        title={`Add ${noun}`}
        loading={saving}
        submitLabel="Create"
        onClose={() => setDialogOpen(false)}
        onSubmit={submitCreate}
      >
        <Typography variant="body2" color="text.secondary">
          Quick create — open Manage for the full form.
        </Typography>
        {(relation.createFields || []).map((f) =>
          f.type === "select" ? (
            <TextField
              key={f.name}
              select
              label={f.label}
              required={f.required}
              fullWidth
              value={draft[f.name] == null ? "" : String(draft[f.name])}
              onChange={(e) =>
                setDraft((prev) => ({ ...prev, [f.name]: e.target.value }))
              }
            >
              {(f.options || []).map((o) => (
                <MenuItem key={o.value} value={o.value}>
                  {o.label}
                </MenuItem>
              ))}
            </TextField>
          ) : (
            <TextField
              key={f.name}
              label={f.label}
              required={f.required}
              type={f.type === "number" ? "number" : f.type === "date" ? "date" : "text"}
              fullWidth
              InputLabelProps={f.type === "date" ? { shrink: true } : undefined}
              placeholder={f.type === "date" ? "YYYY-MM-DD" : undefined}
              helperText={f.type === "number" ? yearHint(f.name) : undefined}
              inputProps={
                f.type === "number"
                  ? (() => {
                      const bounds = numberBounds(f.name);
                      return { min: bounds.min, max: bounds.max, step: bounds.max != null ? 1 : "any" };
                    })()
                  : undefined
              }
              value={draft[f.name] == null ? "" : String(draft[f.name])}
              onBlur={() => {
                if (f.type !== "number") return;
                const bounds = numberBounds(f.name);
                const snapped = snapNumber(draft[f.name], bounds);
                if (snapped !== "" && snapped !== Number(draft[f.name])) {
                  setDraft((prev) => ({ ...prev, [f.name]: snapped }));
                }
              }}
              onChange={(e) =>
                setDraft((prev) => {
                  if (f.type !== "number") return { ...prev, [f.name]: e.target.value };
                  const bounds = numberBounds(f.name);
                  const next = rejectNegative(e.target.value, bounds);
                  if (next == null) return prev;
                  return { ...prev, [f.name]: next === "" ? "" : Number(next) };
                })
              }
            />
          )
        )}
        <Button
          component={Link}
          href={`${relation.listPath}/new`}
          target="_blank"
          rel="noopener noreferrer"
          size="small"
          sx={{ alignSelf: "flex-start" }}
        >
          Open full create form
        </Button>
      </FormDialog>
    </Box>
  );
}

/** Shared relation presets used across ERP forms. */
export const RELATIONS = {
  vendor: {
    apiPath: "/finance/vendors/",
    listPath: "/finance/vendors",
    entityLabel: "Vendor",
    getOptionLabel: (r) => codeNameLabel(r.code, r.name, r.id),
    createFields: [
      { name: "code", label: "Code" },
      { name: "name", label: "Name", required: true },
      { name: "email", label: "Email" },
      { name: "phone", label: "Phone" },
    ],
    createDefaults: { is_active: true },
  } satisfies RelationConfig,
  purchaseOrder: {
    apiPath: "/procurement/orders/",
    listPath: "/procurement/orders",
    entityLabel: "Purchase order",
    getOptionLabel: (r) => {
      const po = String(r.po_no || r.id);
      const vendor = r.vendor_name ? ` · ${r.vendor_name}` : "";
      const amt = r.amount != null ? ` · ${r.amount}` : "";
      return `${po}${vendor}${amt}`;
    },
  } satisfies RelationConfig,
  salesOrder: {
    apiPath: "/sales/orders/",
    listPath: "/sales/orders",
    entityLabel: "Sales order",
    getOptionLabel: (r) => {
      const so = String(r.order_no || r.id);
      const cust = r.customer_name ? ` · ${r.customer_name}` : "";
      return `${so}${cust}`;
    },
  } satisfies RelationConfig,
  arInvoice: {
    apiPath: "/sales/invoices/",
    listPath: "/sales/invoices",
    entityLabel: "AR invoice",
    getOptionLabel: (r) => {
      const no = String(r.invoice_no || r.id);
      const cust = r.customer_name ? ` · ${r.customer_name}` : "";
      const amt = r.amount != null && r.amount !== "" ? ` · ${r.amount}` : "";
      return `${no}${cust}${amt}`;
    },
  } satisfies RelationConfig,
  customer: {
    apiPath: "/sales/customers/",
    listPath: "/sales/customers",
    entityLabel: "Customer",
    getOptionLabel: (r) => codeNameLabel(r.code, r.name, r.id),
    createFields: [
      { name: "code", label: "Code" },
      { name: "name", label: "Name", required: true },
      { name: "email", label: "Email" },
      { name: "phone", label: "Phone" },
    ],
    createDefaults: { is_active: true },
  } satisfies RelationConfig,
  employee: {
    apiPath: "/hr/employees/",
    listPath: "/hr/employees",
    entityLabel: "Employee",
    getOptionLabel: (r) =>
      codeNameLabel(
        r.employee_code,
        `${r.first_name || ""} ${r.last_name || ""}`.trim(),
        r.id
      ),
    createFields: [
      { name: "employee_code", label: "Employee code", required: true },
      { name: "first_name", label: "First name", required: true },
      { name: "last_name", label: "Last name", required: true },
      { name: "email", label: "Email", required: true },
    ],
    createDefaults: { status: "active", is_active: true },
  } satisfies RelationConfig,
  department: {
    apiPath: "/hr/departments/",
    listPath: "/hr/departments",
    entityLabel: "Department",
    getOptionLabel: (r) => codeNameLabel(r.code, r.name, r.id),
    createFields: [
      { name: "code", label: "Code" },
      { name: "name", label: "Name", required: true },
    ],
    allowClear: true,
  } satisfies RelationConfig,
  designation: {
    apiPath: "/hr/designations/",
    listPath: "/hr/designations",
    entityLabel: "Designation",
    getOptionLabel: (r) => codeNameLabel(r.code, r.title, r.id),
    createFields: [
      { name: "code", label: "Code" },
      { name: "title", label: "Title", required: true },
    ],
    allowClear: true,
  } satisfies RelationConfig,
  shift: {
    apiPath: "/hr/shifts/",
    listPath: "/hr/shifts",
    entityLabel: "Shift",
    getOptionLabel: (r) => codeNameLabel(r.code, r.name, r.id),
    createFields: [
      { name: "code", label: "Code" },
      { name: "name", label: "Name", required: true },
      { name: "start_time", label: "Start", defaultValue: "09:00:00" },
      { name: "end_time", label: "End", defaultValue: "18:00:00" },
      { name: "grace_minutes", label: "Grace minutes", type: "number", defaultValue: 15 },
    ],
    allowClear: true,
  } satisfies RelationConfig,
  currency: {
    apiPath: "/finance/currencies/",
    listPath: "/finance/currencies",
    entityLabel: "Currency",
    getOptionLabel: (r) => codeNameLabel(r.code, r.name, r.id),
    getOptionValue: (r) => String(r.code || ""),
    createFields: [
      { name: "code", label: "Code", required: true },
      { name: "name", label: "Name", required: true },
    ],
    createDefaults: { is_active: true },
  } satisfies RelationConfig,
  unitOfMeasure: {
    apiPath: "/inventory/units/",
    listPath: "/inventory/units",
    entityLabel: "Unit",
    getOptionLabel: (r) => codeNameLabel(r.code, r.name, r.id),
    getOptionValue: (r) => String(r.code || ""),
    createFields: [
      { name: "code", label: "Code", required: true },
      { name: "name", label: "Name", required: true },
    ],
    createDefaults: { is_active: true },
  } satisfies RelationConfig,
  costCenter: {
    apiPath: "/finance/cost-centers/",
    listPath: "/finance/cost-centers",
    entityLabel: "Cost center",
    getOptionLabel: (r) => codeNameLabel(r.code, r.name, r.id),
    createFields: [
      { name: "code", label: "Code" },
      { name: "name", label: "Name", required: true },
    ],
    createDefaults: { is_active: true },
    allowClear: true,
  } satisfies RelationConfig,
  payrollPeriod: {
    apiPath: "/payroll/periods/",
    listPath: "/payroll/periods",
    entityLabel: "Payroll period",
    getOptionLabel: (r) => String(r.name || `${r.year}-${r.month}` || r.id),
    createFields: [
      { name: "name", label: "Name", required: true },
      { name: "year", label: "Year", type: "number", required: true },
      { name: "month", label: "Month", type: "number", required: true },
    ],
    createDefaults: { status: "open" },
  } satisfies RelationConfig,
  leaveType: {
    apiPath: "/hr/leave-types/",
    listPath: "/hr/leave-types",
    entityLabel: "Leave type",
    getOptionLabel: (r) => String(r.name || r.code || r.id),
    createFields: [
      { name: "code", label: "Code" },
      { name: "name", label: "Name", required: true },
      { name: "annual_quota", label: "Annual quota", type: "number", defaultValue: 14 },
    ],
  } satisfies RelationConfig,
  bankAccount: {
    apiPath: "/finance/banks/",
    listPath: "/finance/banks",
    entityLabel: "Bank account",
    getOptionLabel: (r) => {
      const title = codeNameLabel(r.name, r.bank_name);
      const no = String(r.account_no || "").trim();
      return no ? `${title} (${no})` : title || String(r.id);
    },
    createFields: [
      { name: "name", label: "Name", required: true },
      { name: "bank_name", label: "Bank name", required: true },
      { name: "account_no", label: "Account no", required: true },
    ],
    createDefaults: { is_active: true, opening_balance: 0 },
  } satisfies RelationConfig,
  item: {
    apiPath: "/inventory/items/",
    listPath: "/inventory/items",
    entityLabel: "Item",
    getOptionLabel: (r) => codeNameLabel(r.sku, r.name, r.id),
    createFields: [
      { name: "sku", label: "SKU", required: true },
      { name: "name", label: "Name", required: true },
      { name: "unit", label: "Unit", defaultValue: "ea" },
    ],
    createDefaults: { is_active: true, qty_on_hand: 0, item_type: "stockable" },
  } satisfies RelationConfig,
  warehouse: {
    apiPath: "/inventory/warehouses/",
    listPath: "/inventory/warehouses",
    entityLabel: "Warehouse",
    getOptionLabel: (r) => codeNameLabel(r.code, r.name, r.id),
    createFields: [
      { name: "code", label: "Code" },
      { name: "name", label: "Name", required: true },
      { name: "address", label: "Address" },
    ],
    createDefaults: { is_active: true },
    allowClear: true,
  } satisfies RelationConfig,
  warehouseBin: {
    apiPath: "/inventory/bins/",
    listPath: "/inventory/bins",
    entityLabel: "Bin",
    getOptionLabel: (r) =>
      r.warehouse_code ? `${r.warehouse_code} / ${r.code}` : String(r.code || r.id),
    allowClear: true,
    clearLabel: "— No bin —",
  } satisfies RelationConfig,
  dmsFolder: {
    apiPath: "/dms/folders/",
    listPath: "/dms/folders",
    entityLabel: "Folder",
    getOptionLabel: (r) =>
      r.parent_name ? `${r.parent_name} / ${r.name}` : String(r.name || r.id),
    createFields: [{ name: "name", label: "Name", required: true }],
    allowClear: true,
    clearLabel: "— None —",
  } satisfies RelationConfig,
  dmsDocumentType: {
    apiPath: "/dms/types/",
    listPath: "/dms/types",
    entityLabel: "Document type",
    getOptionLabel: (r) => String(r.name || r.id),
    createFields: [
      { name: "name", label: "Name", required: true },
      { name: "description", label: "Description" },
    ],
    allowClear: true,
    clearLabel: "— No type —",
  } satisfies RelationConfig,
  dmsTag: {
    apiPath: "/dms/tags/",
    listPath: "/dms/tags",
    entityLabel: "Tag",
    getOptionLabel: (r) => String(r.name || r.id),
    createFields: [{ name: "name", label: "Name", required: true }],
    allowClear: true,
    clearLabel: "— None —",
  } satisfies RelationConfig,
  lead: {
    apiPath: "/crm/leads/",
    listPath: "/crm/leads",
    entityLabel: "Lead",
    getOptionLabel: (r) =>
      r.company ? `${r.name} · ${r.company}` : String(r.name || r.id),
    createFields: [
      { name: "name", label: "Name", required: true },
      { name: "company", label: "Company" },
      { name: "email", label: "Email" },
      { name: "phone", label: "Phone" },
    ],
    createDefaults: { status: "new" },
    allowClear: true,
  } satisfies RelationConfig,
  opportunity: {
    apiPath: "/crm/opportunities/",
    listPath: "/crm/opportunities",
    entityLabel: "Opportunity",
    getOptionLabel: (r) => String(r.name || r.id),
    createFields: [
      { name: "name", label: "Name", required: true },
      { name: "amount", label: "Amount", type: "number", defaultValue: 0 },
    ],
    createDefaults: { stage: "prospecting" },
    allowClear: true,
  } satisfies RelationConfig,
  project: {
    apiPath: "/projects/projects/",
    listPath: "/projects",
    entityLabel: "Project",
    getOptionLabel: (r) => codeNameLabel(r.code, r.name, r.id),
    createFields: [
      { name: "code", label: "Code" },
      { name: "name", label: "Name", required: true },
    ],
    createDefaults: { status: "draft", budget_amount: 0 },
  } satisfies RelationConfig,
  projectTask: {
    apiPath: "/projects/tasks/",
    listPath: "/projects/tasks",
    entityLabel: "Project task",
    getOptionLabel: (r) =>
      r.project_code ? `${r.project_code} · ${r.name}` : String(r.name || r.id),
    allowClear: true,
    clearLabel: "— None —",
  } satisfies RelationConfig,
  icPartner: {
    apiPath: "/finance/intercompany/",
    listPath: "/finance/intercompany",
    entityLabel: "IC partner",
    getOptionLabel: (r) => codeNameLabel(r.code, r.name, r.id),
    createFields: [
      { name: "code", label: "Code" },
      { name: "name", label: "Name", required: true },
    ],
    createDefaults: { is_active: true, currency: "PKR" },
  } satisfies RelationConfig,
  bom: {
    apiPath: "/mfg/boms/",
    listPath: "/mfg/boms",
    entityLabel: "BOM",
    getOptionLabel: (r) => codeNameLabel(r.code, r.name, r.id),
    createFields: [
      { name: "code", label: "Code" },
      { name: "name", label: "Name", required: true },
    ],
    createDefaults: { is_active: true },
    allowClear: true,
  } satisfies RelationConfig,
  fixedAsset: {
    apiPath: "/finance/assets/",
    listPath: "/finance/assets",
    entityLabel: "Fixed asset",
    getOptionLabel: (r) => codeNameLabel(r.asset_code, r.name, r.id),
  } satisfies RelationConfig,
  goodsReceipt: {
    apiPath: "/procurement/receipts/",
    listPath: "/procurement/receipts",
    entityLabel: "Goods receipt",
    getOptionLabel: (r) => {
      const grn = String(r.grn_no || r.id);
      const vendor = r.vendor_name ? ` · ${r.vendor_name}` : "";
      return `${grn}${vendor}`;
    },
    allowClear: true,
    clearLabel: "— None —",
  } satisfies RelationConfig,
  ncr: {
    apiPath: "/qms/ncrs/",
    listPath: "/qms/ncrs",
    entityLabel: "NCR",
    getOptionLabel: (r) => codeNameLabel(r.ncr_no, r.title, r.id),
  } satisfies RelationConfig,
  qualityInspection: {
    apiPath: "/qms/inspections/",
    listPath: "/qms/inspections",
    entityLabel: "Inspection",
    getOptionLabel: (r) => {
      const no = String(r.inspection_no || r.id);
      return r.item_sku ? `${no} · ${r.item_sku}` : no;
    },
    allowClear: true,
    clearLabel: "— None —",
  } satisfies RelationConfig,
  account: {
    apiPath: "/finance/accounts/",
    listPath: "/finance/accounts",
    entityLabel: "Account",
    getOptionLabel: (r) => codeNameLabel(r.code, r.name, r.id),
    createFields: [
      { name: "code", label: "Code" },
      { name: "name", label: "Name", required: true },
      { name: "account_type", label: "Type", defaultValue: "expense" },
    ],
    createDefaults: { is_active: true },
    allowClear: true,
    clearLabel: "— None —",
  } satisfies RelationConfig,
  user: {
    apiPath: "/settings/users/",
    listPath: "/settings/users",
    entityLabel: "User",
    getOptionLabel: (r) =>
      String(r.username || r.email || `${r.first_name || ""} ${r.last_name || ""}`.trim() || r.id),
    allowClear: true,
    clearLabel: "— Not linked (no ESS) —",
  } satisfies RelationConfig,
  accountType: {
    apiPath: "/finance/account-types/",
    listPath: "/finance/account-types",
    entityLabel: "Account type",
    getOptionLabel: (r) => {
      const base = codeNameLabel(r.code, r.name);
      const stmt = String(r.statement_class || "").trim();
      const pretty = stmt ? stmt.charAt(0).toUpperCase() + stmt.slice(1) : "";
      if (!pretty || sameToken(stmt, r.code) || sameToken(stmt, r.name) || sameToken(stmt, base)) {
        return distinctLabel(base);
      }
      return distinctLabel(base, pretty);
    },
    getOptionValue: (r) => String(r.code || ""),
    createFields: [
      { name: "code", label: "Code" },
      { name: "name", label: "Name", required: true },
      {
        name: "statement_class",
        label: "Statement class",
        type: "select",
        required: true,
        defaultValue: "expense",
        options: [
          { value: "asset", label: "Asset (Balance sheet)" },
          { value: "liability", label: "Liability (Balance sheet)" },
          { value: "equity", label: "Equity (Balance sheet)" },
          { value: "income", label: "Income (P&L)" },
          { value: "expense", label: "Expense (P&L)" },
        ],
      },
    ],
    createDefaults: { is_active: true, is_system: false, sort: 100 },
  } satisfies RelationConfig,
} as const;
