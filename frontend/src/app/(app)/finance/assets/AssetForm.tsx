"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Box,
  Button,
  Chip,
  Divider,
  MenuItem,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import DateTextField, { todayISO } from "@/components/DateTextField";
import EditIcon from "@mui/icons-material/Edit";
import PrintIcon from "@mui/icons-material/Print";
import BuildIcon from "@mui/icons-material/Build";
import FormPageShell from "@/components/crud/FormPageShell";
import { DetailSection } from "@/components/crud/DetailPageShell";
import RelationSelect, { RELATIONS } from "@/components/crud/RelationSelect";
import ModuleGate from "@/components/ModuleGate";
import { useEntityForm, type FormMode } from "@/hooks/useEntityForm";
import { usePermissions } from "@/hooks/usePermissions";
import { createResource, listResource } from "@/lib/crudApi";
import api from "@/lib/api";
import { useSnackbar } from "notistack";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { numberBounds, rejectNegative } from "@/lib/numberBounds";

type Emp = {
  id: number;
  employee_code: string;
  first_name: string;
  last_name: string;
};

type Repair = {
  id: number;
  request_no: string;
  title: string;
  status: string;
  requested_on?: string | null;
  cost?: string | number;
  vendor_name?: string;
};

const MODULE = "finance.assets";
const BASE = "/finance/assets";
const API = "/finance/assets/";
const REPAIR_API = "/finance/asset-repairs/";

const STATUSES = ["active", "in_repair", "idle", "disposed"] as const;
const CATEGORIES = [
  "IT equipment",
  "Furniture",
  "Vehicle",
  "Machinery",
  "Building",
  "Other",
];
const REPAIR_STATUSES = [
  "requested",
  "approved",
  "in_progress",
  "completed",
  "cancelled",
] as const;

const empty = {
  asset_code: "",
  name: "",
  category: "",
  location: "",
  custodian: "",
  assigned_employee: "",
  purchase_date: todayISO(),
  purchase_cost: "0",
  depreciation_rate: "0",
  book_value: "0",
  accumulated_depreciation: "0",
  status: "active",
  qr_payload: "",
  qr_url: "",
};

function qrImageSrc(payload: string) {
  return `https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(
    payload
  )}`;
}

export default function AssetForm({ mode, id }: { mode: FormMode; id?: string }) {
  const { canChange, canAdd } = usePermissions();
  const { enqueueSnackbar } = useSnackbar();
  const [employees, setEmployees] = useState<Emp[]>([]);
  const [repairs, setRepairs] = useState<Repair[]>([]);
  const [repairBusy, setRepairBusy] = useState(false);
  const [busy, setBusy] = useState(false);
  const [repairForm, setRepairForm] = useState({
    title: "",
    description: "",
    vendor_name: "",
    cost: "0",
    status: "requested",
  });

  const { form, setForm, loading, saving, save, reload, readOnly } = useEntityForm({
    resourcePath: API,
    entityLabel: "Fixed asset",
    basePath: BASE,
    mode,
    id,
    empty,
    mapLoaded: (row) => ({
      asset_code: String(row.asset_code ?? ""),
      name: String(row.name ?? ""),
      category: String(row.category ?? ""),
      location: String(row.location ?? ""),
      custodian: String(row.custodian ?? ""),
      assigned_employee: row.assigned_employee
        ? String(row.assigned_employee)
        : "",
      purchase_date: String(row.purchase_date ?? ""),
      purchase_cost: String(row.purchase_cost ?? "0"),
      depreciation_rate: String(row.depreciation_rate ?? "0"),
      book_value: String(row.book_value ?? "0"),
      accumulated_depreciation: String(row.accumulated_depreciation ?? "0"),
      status: String(row.status ?? "active"),
      qr_payload: String(row.qr_payload ?? ""),
      qr_url: String(row.qr_url ?? ""),
    }),
    mapPayload: (f) => ({
      asset_code: f.asset_code,
      name: f.name,
      category: f.category,
      location: f.location,
      custodian: f.custodian,
      assigned_employee: f.assigned_employee
        ? Number(f.assigned_employee)
        : null,
      purchase_date: f.purchase_date || null,
      purchase_cost: f.purchase_cost ? Number(f.purchase_cost) : 0,
      depreciation_rate: f.depreciation_rate
        ? Number(f.depreciation_rate)
        : 0,
      book_value: f.book_value ? Number(f.book_value) : 0,
      status: f.status,
    }),
  });

  useEffect(() => {
    listResource<Emp>("/hr/employees/")
      .then(setEmployees)
      .catch(() => undefined);
  }, []);

  const loadRepairs = useCallback(async () => {
    if (!id || mode === "create") return;
    try {
      const rows = await listResource<Repair>(REPAIR_API, { asset: id });
      setRepairs(rows);
    } catch {
      setRepairs([]);
    }
  }, [id, mode]);

  useEffect(() => {
    loadRepairs();
  }, [loadRepairs]);

  const runDepreciate = async () => {
    if (!id) return;
    if (
      !window.confirm(
        "Post one annual straight-line depreciation slice to this asset’s book value?"
      )
    ) {
      return;
    }
    setBusy(true);
    try {
      const { data } = await api.post(`${API}${id}/depreciate/`);
      enqueueSnackbar(
        `Depreciation ${data?.depreciation ?? ""} · WDV ${data?.book_value ?? ""}${
          data?.gl_journal_ref ? ` · GL ${data.gl_journal_ref}` : ""
        }`,
        { variant: "success" }
      );
      await reload();
    } catch (e) {
      enqueueSnackbar(
        getApiErrorMessage(e, "Depreciation failed"),
        errorSnackbarOpts
      );
    } finally {
      setBusy(false);
    }
  };

  const runDispose = async () => {
    if (!id) return;
    const proceeds = window.prompt("Disposal proceeds (PKR)", "0") ?? "";
    if (proceeds === "") return;
    if (!window.confirm("Mark this asset as disposed? This cannot be undone easily.")) {
      return;
    }
    setBusy(true);
    try {
      await api.post(`${API}${id}/dispose/`, {
        proceeds: Number(proceeds) || 0,
      });
      enqueueSnackbar("Asset disposed", { variant: "success" });
      await reload();
    } catch (e) {
      enqueueSnackbar(getApiErrorMessage(e, "Dispose failed"), errorSnackbarOpts);
    } finally {
      setBusy(false);
    }
  };

  const onAssigneeChange = (value: string) => {
    const emp = employees.find((e) => String(e.id) === value);
    setForm({
      ...form,
      assigned_employee: value,
      custodian: emp
        ? `${emp.first_name} ${emp.last_name}`.trim()
        : form.custodian,
    });
  };

  const createRepair = async () => {
    if (!id || !repairForm.title.trim()) {
      enqueueSnackbar("Repair title is required", { variant: "warning" });
      return;
    }
    setRepairBusy(true);
    try {
      const today = todayISO();
      await createResource(REPAIR_API, {
        asset: Number(id),
        title: repairForm.title,
        description: repairForm.description,
        vendor_name: repairForm.vendor_name,
        cost: Number(repairForm.cost) || 0,
        status: repairForm.status,
        requested_on: today,
      });
      enqueueSnackbar("Repair request created", { variant: "success" });
      setRepairForm({
        title: "",
        description: "",
        vendor_name: "",
        cost: "0",
        status: "requested",
      });
      await loadRepairs();
      const { data } = await api.get(`${API}${id}/`);
      if (data?.status) {
        setForm((prev) => ({ ...prev, status: String(data.status) }));
      }
    } catch (e: unknown) {
      enqueueSnackbar(
        getApiErrorMessage(e, "Could not create repair"),
        errorSnackbarOpts
      );
    } finally {
      setRepairBusy(false);
    }
  };

  const updateRepairStatus = async (repairId: number, status: string) => {
    setRepairBusy(true);
    try {
      const payload: Record<string, unknown> = { status };
      if (status === "completed") {
        payload.completed_on = todayISO();
      }
      await api.patch(`${REPAIR_API}${repairId}/`, payload);
      enqueueSnackbar("Repair updated", { variant: "success" });
      await loadRepairs();
      if (id) {
        const { data } = await api.get(`${API}${id}/`);
        if (data?.status) {
          setForm((prev) => ({ ...prev, status: String(data.status) }));
        }
      }
    } catch (e: unknown) {
      enqueueSnackbar(
        getApiErrorMessage(e, "Could not update repair"),
        errorSnackbarOpts
      );
    } finally {
      setRepairBusy(false);
    }
  };

  const title =
    mode === "create"
      ? "Record an asset"
      : mode === "edit"
        ? "Edit asset"
        : "Asset";

  const stickerPayload =
    form.qr_payload ||
    (id
      ? `SIERP-ASSET|${form.asset_code}|/finance/assets/${id}`
      : form.asset_code);

  return (
    <ModuleGate module={MODULE}>
      <FormPageShell
        title={title}
        subtitle={
          mode === "view"
            ? "Who has it, what it cost, and what it is worth now."
            : "What you bought, what it cost, and how fast it wears out."
        }
        backHref={BASE}
        mode={mode}
        loading={loading}
        saving={saving}
        onSubmit={save}
        submitLabel="Save and close"
        extraActions={
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {mode === "view" && canChange(MODULE) && id && form.status === "active" ? (
              <>
                <Button
                  size="small"
                  variant="outlined"
                  disabled={busy}
                  onClick={runDepreciate}
                >
                  Post annual depreciation
                </Button>
                <Button
                  size="small"
                  color="warning"
                  variant="outlined"
                  disabled={busy}
                  onClick={runDispose}
                >
                  Dispose
                </Button>
              </>
            ) : null}
            {mode === "view" && canChange(MODULE) && id ? (
              <Button
                component={Link}
                href={`${BASE}/${id}/edit`}
                variant="contained"
                startIcon={<EditIcon />}
              >
                Edit
              </Button>
            ) : null}
          </Stack>
        }
      >
        <TextField
          label="Asset code"
          required
          fullWidth
          value={form.asset_code}
          disabled={readOnly || mode === "edit"}
          onChange={(e) => setForm({ ...form, asset_code: e.target.value })}
        />
        <TextField
          label="Name"
          required
          fullWidth
          value={form.name}
          disabled={readOnly}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
        />
        <TextField
          select
          label="Category"
          fullWidth
          value={form.category}
          disabled={readOnly}
          onChange={(e) => setForm({ ...form, category: e.target.value })}
        >
          <MenuItem value="">—</MenuItem>
          {CATEGORIES.map((c) => (
            <MenuItem key={c} value={c}>
              {c}
            </MenuItem>
          ))}
          {form.category && !CATEGORIES.includes(form.category) ? (
            <MenuItem value={form.category}>{form.category}</MenuItem>
          ) : null}
        </TextField>
        <TextField
          select
          label="Status"
          fullWidth
          value={form.status}
          disabled={readOnly}
          onChange={(e) => setForm({ ...form, status: e.target.value })}
        >
          {STATUSES.map((s) => (
            <MenuItem key={s} value={s}>
              {s}
            </MenuItem>
          ))}
        </TextField>
        <RelationSelect
          label="Assigned employee"
          value={form.assigned_employee}
          disabled={readOnly}
          helperText="The person who has this item."
          relation={{
            ...RELATIONS.employee,
            allowClear: true,
            clearLabel: "— Unassigned —",
          }}
          onChange={(v) => onAssigneeChange(v)}
        />
        <TextField
          label="Location"
          fullWidth
          value={form.location}
          disabled={readOnly}
          onChange={(e) => setForm({ ...form, location: e.target.value })}
        />
        <TextField
          label="Custodian"
          fullWidth
          value={form.custodian}
          disabled={readOnly}
          onChange={(e) => setForm({ ...form, custodian: e.target.value })}
        />
        <TextField
          label="Purchase date"
          type="date"
          placeholder="YYYY-MM-DD"
          helperText="Pick a date - YYYY-MM-DD"
          fullWidth
          InputLabelProps={{ shrink: true }}
          value={form.purchase_date}
          disabled={readOnly}
          onChange={(e) => setForm({ ...form, purchase_date: e.target.value })}
        />
        <TextField
          label="Purchase cost"
          type="number"
          fullWidth
          value={form.purchase_cost}
          disabled={readOnly}
          inputProps={{ min: 0, step: "0.01" }}
          onChange={(e) => {
            const next = rejectNegative(e.target.value, { min: 0 });
            if (next == null) return;
            setForm({ ...form, purchase_cost: next });
          }}
        />
        <TextField
          label="Yearly wear-down %"
          type="number"
          fullWidth
          value={form.depreciation_rate}
          disabled={readOnly}
          inputProps={numberBounds("depreciation_rate")}
          helperText="Percent of the cost used up each year. Run it from the asset's page."
          onChange={(e) => {
            const next = rejectNegative(e.target.value, numberBounds("depreciation_rate"));
            if (next == null) return;
            setForm({ ...form, depreciation_rate: next });
          }}
        />
        <TextField
          label="Worn down so far"
          type="number"
          fullWidth
          value={form.accumulated_depreciation}
          disabled
          helperText="Filled in when you record a month of wear-down."
        />
        <TextField
          label="Value now"
          type="number"
          fullWidth
          value={form.book_value}
          disabled={readOnly}
          inputProps={{ min: 0, step: "0.01" }}
          helperText="Cost minus what has worn down."
          onChange={(e) => {
            const next = rejectNegative(e.target.value, { min: 0 });
            if (next == null) return;
            setForm({ ...form, book_value: next });
          }}
        />

        {mode === "view" && id ? (
          <>
            <Divider />
            <Stack
              direction={{ xs: "column", sm: "row" }}
              spacing={2}
              alignItems={{ xs: "stretch", sm: "flex-start" }}
            >
              <Box
                sx={{
                  p: 2,
                  border: "1px dashed",
                  borderColor: "divider",
                  borderRadius: 1,
                  textAlign: "center",
                  minWidth: 200,
                }}
              >
                <Typography variant="subtitle2" gutterBottom>
                  QR sticker
                </Typography>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={qrImageSrc(stickerPayload)}
                  alt={`QR for ${form.asset_code}`}
                  width={180}
                  height={180}
                  style={{ display: "block", margin: "0 auto" }}
                />
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ display: "block", mt: 1, wordBreak: "break-all" }}
                >
                  {form.asset_code}
                </Typography>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ display: "block", wordBreak: "break-all" }}
                >
                  {form.qr_url || `/finance/assets/${id}`}
                </Typography>
                <Button
                  size="small"
                  startIcon={<PrintIcon />}
                  sx={{ mt: 1 }}
                  onClick={() => window.print()}
                >
                  Print sticker
                </Button>
              </Box>
              <Box flex={1}>
                <Typography variant="body2" color="text.secondary">
                  Scan payload encodes organization asset code and deep link for
                  inventory stickers.
                </Typography>
                <TextField
                  label="QR payload"
                  fullWidth
                  multiline
                  minRows={2}
                  value={stickerPayload}
                  InputProps={{ readOnly: true }}
                  sx={{ mt: 1.5 }}
                />
              </Box>
            </Stack>

            <DetailSection
              title="Repairs"
              description={`${repairs.length} record(s)`}
              defaultExpanded
              action={<Chip size="small" icon={<BuildIcon />} label={`${repairs.length}`} />}
            >

            {canAdd(MODULE) || canChange(MODULE) ? (
              <Stack spacing={1.5}>
                <TextField
                  label="Repair title"
                  fullWidth
                  value={repairForm.title}
                  onChange={(e) =>
                    setRepairForm({ ...repairForm, title: e.target.value })
                  }
                />
                <TextField
                  label="Description"
                  fullWidth
                  multiline
                  minRows={2}
                  value={repairForm.description}
                  onChange={(e) =>
                    setRepairForm({
                      ...repairForm,
                      description: e.target.value,
                    })
                  }
                />
                <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
                  <TextField
                    label="Vendor"
                    fullWidth
                    value={repairForm.vendor_name}
                    onChange={(e) =>
                      setRepairForm({
                        ...repairForm,
                        vendor_name: e.target.value,
                      })
                    }
                  />
                  <TextField
                    label="Est. cost"
                    type="number"
                    fullWidth
                    value={repairForm.cost}
                    inputProps={{ min: 0, step: "0.01" }}
                    onChange={(e) => {
                      const next = rejectNegative(e.target.value, { min: 0 });
                      if (next == null) return;
                      setRepairForm({ ...repairForm, cost: next });
                    }}
                  />
                  <TextField
                    select
                    label="Status"
                    fullWidth
                    value={repairForm.status}
                    onChange={(e) =>
                      setRepairForm({ ...repairForm, status: e.target.value })
                    }
                  >
                    {REPAIR_STATUSES.map((s) => (
                      <MenuItem key={s} value={s}>
                        {s}
                      </MenuItem>
                    ))}
                  </TextField>
                </Stack>
                <Button
                  variant="outlined"
                  disabled={repairBusy}
                  onClick={createRepair}
                  startIcon={<BuildIcon />}
                >
                  Create repair request
                </Button>
              </Stack>
            ) : null}

            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Request</TableCell>
                  <TableCell>Title</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Date</TableCell>
                  <TableCell align="right">Action</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {repairs.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5}>
                      <Typography variant="body2" color="text.secondary">
                        No repair records yet.
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  repairs.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell>{r.request_no}</TableCell>
                      <TableCell>{r.title}</TableCell>
                      <TableCell>
                        <Chip size="small" label={r.status} variant="outlined" />
                      </TableCell>
                      <TableCell>{r.requested_on || "—"}</TableCell>
                      <TableCell align="right">
                        {canChange(MODULE) &&
                        r.status !== "completed" &&
                        r.status !== "cancelled" ? (
                          <Stack
                            direction="row"
                            spacing={0.5}
                            justifyContent="flex-end"
                          >
                            {r.status === "requested" ? (
                              <Button
                                size="small"
                                disabled={repairBusy}
                                onClick={() =>
                                  updateRepairStatus(r.id, "in_progress")
                                }
                              >
                                Start
                              </Button>
                            ) : null}
                            <Button
                              size="small"
                              disabled={repairBusy}
                              onClick={() =>
                                updateRepairStatus(r.id, "completed")
                              }
                            >
                              Complete
                            </Button>
                            <Button
                              size="small"
                              color="inherit"
                              disabled={repairBusy}
                              onClick={() =>
                                updateRepairStatus(r.id, "cancelled")
                              }
                            >
                              Cancel
                            </Button>
                          </Stack>
                        ) : (
                          "—"
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
            </DetailSection>
          </>
        ) : null}
      </FormPageShell>
    </ModuleGate>
  );
}
