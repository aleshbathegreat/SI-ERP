"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  Box,
  Button,
  Checkbox,
  Chip,
  Divider,
  FormControlLabel,
  FormGroup,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import { useSnackbar } from "notistack";
import FormPageShell from "@/components/crud/FormPageShell";
import PlatformGate from "@/components/PlatformGate";
import { type FormMode } from "@/hooks/useEntityForm";
import api from "@/lib/api";
import { createResource, getResource, updateResource } from "@/lib/crudApi";

type CatalogModule = { key: string; label: string; core: boolean };
type CatalogGroup = {
  id: string;
  label: string;
  core: boolean;
  modules: CatalogModule[];
};

const basePath = "/platform/packages";
const resourcePath = "/platform/packages/";

const empty = {
  name: "",
  code: "",
  price: "0",
  interval: "month",
  summary: "",
  module_keys: [] as string[],
  core_module_keys: [] as string[],
  max_functional_users: 10,
  max_ess_users: 50,
  max_attendance_devices: 0,
  attendance_connectors: [] as string[],
  active: true,
  sort: 0,
};

const PRESETS: { label: string; keys: string[] }[] = [
  { label: "Full ERP", keys: ["finance", "hr", "payroll", "billing"] },
  { label: "Finance only", keys: ["finance", "billing"] },
  { label: "HR + Payroll", keys: ["hr", "payroll", "billing"] },
];

export default function PackageForm({ mode }: { mode: FormMode }) {
  const params = useParams();
  const id = mode === "create" ? undefined : String(params.id);
  const router = useRouter();
  const { enqueueSnackbar } = useSnackbar();
  const [form, setForm] = useState(empty);
  const [groups, setGroups] = useState<CatalogGroup[]>([]);
  const [coreKeys, setCoreKeys] = useState<string[]>([]);
  const [connectorOptions, setConnectorOptions] = useState<
    { key: string; name: string; vendor: string; tier: string }[]
  >([]);
  const [loading, setLoading] = useState(mode !== "create");
  const [saving, setSaving] = useState(false);
  const readOnly = mode === "view";

  useEffect(() => {
    api
      .get<{
        groups: CatalogGroup[];
        core_keys: string[];
        assignable_keys: string[];
      }>("/platform/module-catalog/")
      .then((r) => {
        setGroups(r.data.groups || []);
        setCoreKeys(r.data.core_keys || []);
      })
      .catch(() => setGroups([]));
    api
      .get<{ connectors: { key: string; name: string; vendor: string; tier: string }[] }>(
        "/hr/attendance/connectors/"
      )
      .then((r) => setConnectorOptions(r.data.connectors || []))
      .catch(() =>
        // Fallback static list if tenant catalog blocked for platform user
        setConnectorOptions([
          { key: "zkteco_adms", name: "ZKTeco ADMS", vendor: "ZKTeco", tier: "standard" },
          { key: "zkteco_biotime", name: "BioTime", vendor: "ZKTeco", tier: "professional" },
          { key: "hikvision_isapi", name: "Hikvision ISAPI", vendor: "Hikvision", tier: "professional" },
          { key: "dahua_dss", name: "Dahua DSS", vendor: "Dahua", tier: "professional" },
          { key: "anviz_crosschex", name: "Anviz", vendor: "Anviz", tier: "standard" },
          { key: "suprema_biostar", name: "BioStar 2", vendor: "Suprema", tier: "enterprise" },
          { key: "essl_biomax", name: "eSSL / Biomax", vendor: "eSSL", tier: "standard" },
          { key: "realand", name: "Realand", vendor: "Realand", tier: "standard" },
          { key: "idemia_morpho", name: "IDEMIA Morpho", vendor: "IDEMIA", tier: "enterprise" },
          { key: "timetec_biotime", name: "FingerTec / TimeTec", vendor: "TimeTec", tier: "professional" },
          { key: "generic_webhook", name: "Generic webhook", vendor: "Generic", tier: "standard" },
          { key: "generic_csv", name: "CSV import", vendor: "Generic", tier: "standard" },
        ])
      );
  }, []);

  useEffect(() => {
    if (mode === "create") {
      setForm({ ...empty, core_module_keys: coreKeys, module_keys: [] });
      setLoading(false);
      return;
    }
    if (id == null) return;
    setLoading(true);
    getResource<Record<string, unknown>>(resourcePath, id)
      .then((row) => {
        setForm({
          name: String(row.name ?? ""),
          code: String(row.code ?? ""),
          price: String(row.price ?? "0"),
          interval: String(row.interval ?? "month"),
          summary: String(row.summary ?? ""),
          module_keys: (row.module_keys as string[]) || [],
          core_module_keys:
            (row.core_module_keys as string[])?.length
              ? (row.core_module_keys as string[])
              : coreKeys,
          max_functional_users: Number(row.max_functional_users ?? 10),
          max_ess_users: Number(row.max_ess_users ?? 50),
          max_attendance_devices: Number(row.max_attendance_devices ?? 0),
          attendance_connectors: (row.attendance_connectors as string[]) || [],
          active: !!row.active,
          sort: Number(row.sort ?? 0),
        });
      })
      .catch(() => {
        enqueueSnackbar("Failed to load Package", { variant: "error" });
        router.replace(basePath);
      })
      .finally(() => setLoading(false));
  }, [mode, id, coreKeys, enqueueSnackbar, router]);

  const assignableGroups = useMemo(() => groups.filter((g) => !g.core), [groups]);
  const coreGroup = useMemo(() => groups.find((g) => g.core), [groups]);
  const selectedCount = form.module_keys.length;
  const coreCount = (form.core_module_keys.length || coreKeys.length) || 0;

  const toggleModule = (key: string, checked: boolean) => {
    setForm((prev) => {
      const set = new Set(prev.module_keys);
      if (checked) set.add(key);
      else set.delete(key);
      return { ...prev, module_keys: Array.from(set).sort() };
    });
  };

  const toggleGroup = (keys: string[], checked: boolean) => {
    setForm((prev) => {
      const set = new Set(prev.module_keys);
      keys.forEach((k) => (checked ? set.add(k) : set.delete(k)));
      return { ...prev, module_keys: Array.from(set).sort() };
    });
  };

  const applyPreset = (presetKeys: string[]) => {
    const expanded = new Set<string>();
    for (const alias of presetKeys) {
      if (alias === "finance") {
        assignableGroups.find((g) => g.id === "finance")?.modules.forEach((m) => expanded.add(m.key));
      } else if (alias === "hr") {
        assignableGroups.find((g) => g.id === "hr")?.modules.forEach((m) => expanded.add(m.key));
      } else if (alias === "payroll") {
        assignableGroups.find((g) => g.id === "payroll")?.modules.forEach((m) => expanded.add(m.key));
      } else if (alias === "billing") {
        expanded.add("billing");
      }
    }
    setForm((prev) => ({ ...prev, module_keys: Array.from(expanded).sort() }));
  };

  const save = async () => {
    if (mode === "view") {
      router.push(basePath);
      return;
    }
    setSaving(true);
    try {
      const payload = {
        ...form,
        module_keys: form.module_keys,
        core_module_keys: form.core_module_keys.length ? form.core_module_keys : coreKeys,
      };
      if (mode === "edit" && id != null) {
        await updateResource(resourcePath, id, payload);
        enqueueSnackbar("Package updated", { variant: "success" });
      } else {
        await createResource(resourcePath, payload);
        enqueueSnackbar("Package created", { variant: "success" });
      }
      router.push(basePath);
    } catch (e: unknown) {
      const detail =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Could not save Package";
      enqueueSnackbar(String(detail), { variant: "error" });
    } finally {
      setSaving(false);
    }
  };

  const title =
    mode === "create" ? "New package" : mode === "edit" ? "Edit package" : "View package";

  return (
    <PlatformGate capability="packages">
      <FormPageShell
        title={title}
        subtitle="Core modules are always on · assign product modules per plan"
        backHref={basePath}
        mode={mode}
        loading={loading}
        saving={saving}
        onSubmit={save}
        maxWidth={960}
        extraActions={
          mode === "view" && id ? (
            <Button
              component={Link}
              href={`${basePath}/${id}/edit`}
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
          value={form.name}
          disabled={readOnly}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
        />
        <TextField
          label="Code"
          required
          value={form.code}
          disabled={readOnly || mode === "edit"}
          helperText="Slug unique id (e.g. monthly)"
          onChange={(e) => setForm({ ...form, code: e.target.value })}
        />
        <Stack direction="row" spacing={1}>
          <TextField
            label="Price"
            value={form.price}
            disabled={readOnly}
            fullWidth
            onChange={(e) => setForm({ ...form, price: e.target.value })}
          />
          <TextField
            select
            label="Interval"
            value={form.interval}
            disabled={readOnly}
            fullWidth
            onChange={(e) => setForm({ ...form, interval: e.target.value })}
          >
            <MenuItem value="trial">Trial</MenuItem>
            <MenuItem value="month">Monthly</MenuItem>
            <MenuItem value="year">Annual</MenuItem>
          </TextField>
        </Stack>
        <TextField
          label="Summary"
          multiline
          minRows={2}
          value={form.summary}
          disabled={readOnly}
          onChange={(e) => setForm({ ...form, summary: e.target.value })}
        />

        <Divider />
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
          <Typography variant="subtitle2">Module entitlement</Typography>
          <Chip size="small" label={`${coreCount} core`} color="success" variant="outlined" />
          <Chip size="small" label={`${selectedCount} assignable`} color="primary" />
          {!readOnly
            ? PRESETS.map((p) => (
                <Button key={p.label} size="small" variant="outlined" onClick={() => applyPreset(p.keys)}>
                  {p.label}
                </Button>
              ))
            : null}
        </Stack>

        {coreGroup ? (
          <Box
            sx={{
              p: 1.5,
              borderRadius: 2,
              border: "1px solid",
              borderColor: "divider",
              bgcolor: (t) =>
                t.palette.mode === "dark" ? "rgba(76,175,122,0.08)" : "rgba(46,125,79,0.06)",
            }}
          >
            <Typography variant="subtitle2" gutterBottom>
              {coreGroup.label}
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block" mb={1}>
              Locked on every package — dashboard, approvals, ESS, and governance settings.
            </Typography>
            <Stack direction="row" flexWrap="wrap" useFlexGap spacing={0.75}>
              {coreGroup.modules.map((m) => (
                <Chip key={m.key} size="small" label={m.label} color="success" variant="outlined" />
              ))}
            </Stack>
          </Box>
        ) : null}

        {assignableGroups.map((g) => {
          const keys = g.modules.map((m) => m.key);
          const allOn = keys.every((k) => form.module_keys.includes(k));
          const someOn = keys.some((k) => form.module_keys.includes(k));
          return (
            <Box
              key={g.id}
              sx={{ p: 1.5, borderRadius: 2, border: "1px solid", borderColor: "divider" }}
            >
              <Stack direction="row" justifyContent="space-between" alignItems="center" mb={0.5}>
                <Typography variant="subtitle2">{g.label}</Typography>
                {!readOnly ? (
                  <FormControlLabel
                    control={
                      <Checkbox
                        size="small"
                        checked={allOn}
                        indeterminate={someOn && !allOn}
                        onChange={(e) => toggleGroup(keys, e.target.checked)}
                      />
                    }
                    label={<Typography variant="caption">All</Typography>}
                  />
                ) : null}
              </Stack>
              <FormGroup>
                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
                    gap: 0.25,
                  }}
                >
                  {g.modules.map((m) => (
                    <FormControlLabel
                      key={m.key}
                      control={
                        <Checkbox
                          size="small"
                          checked={form.module_keys.includes(m.key)}
                          disabled={readOnly}
                          onChange={(e) => toggleModule(m.key, e.target.checked)}
                        />
                      }
                      label={
                        <Typography variant="body2" title={m.key}>
                          {m.label}
                        </Typography>
                      }
                    />
                  ))}
                </Box>
              </FormGroup>
            </Box>
          );
        })}

        <Stack direction="row" spacing={1}>
          <TextField
            type="number"
            label="Max functional"
            value={form.max_functional_users}
            disabled={readOnly}
            fullWidth
            onChange={(e) =>
              setForm({ ...form, max_functional_users: Number(e.target.value) || 0 })
            }
          />
          <TextField
            type="number"
            label="Max ESS"
            value={form.max_ess_users}
            disabled={readOnly}
            fullWidth
            onChange={(e) => setForm({ ...form, max_ess_users: Number(e.target.value) || 0 })}
          />
          <TextField
            type="number"
            label="Sort"
            value={form.sort}
            disabled={readOnly}
            fullWidth
            onChange={(e) => setForm({ ...form, sort: Number(e.target.value) || 0 })}
          />
        </Stack>

        <Divider />
        <Typography variant="subtitle2">Attendance devices (package gate)</Typography>
        <Typography variant="body2" color="text.secondary">
          Enable module <code>hr.attendance_devices</code> above, then cap devices and pick
          allowed market connectors for tenants on this package.
        </Typography>
        <TextField
          type="number"
          label="Max attendance devices"
          value={form.max_attendance_devices}
          disabled={readOnly}
          fullWidth
          helperText="0 = no devices even if module is on"
          onChange={(e) =>
            setForm({
              ...form,
              max_attendance_devices: Number(e.target.value) || 0,
            })
          }
        />
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <Button
            size="small"
            disabled={readOnly}
            onClick={() => setForm({ ...form, attendance_connectors: ["*"] })}
          >
            Allow all connectors
          </Button>
          <Button
            size="small"
            disabled={readOnly}
            onClick={() => setForm({ ...form, attendance_connectors: [] })}
          >
            Clear connectors
          </Button>
        </Stack>
        {form.attendance_connectors.includes("*") ? (
          <Chip label="All market connectors (*)" color="success" size="small" />
        ) : (
          <FormGroup>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
                gap: 0.5,
              }}
            >
              {connectorOptions.map((c) => {
                const checked = form.attendance_connectors.includes(c.key);
                return (
                  <FormControlLabel
                    key={c.key}
                    control={
                      <Checkbox
                        size="small"
                        checked={checked}
                        disabled={readOnly}
                        onChange={(e) => {
                          setForm((prev) => {
                            const set = new Set(prev.attendance_connectors);
                            if (e.target.checked) set.add(c.key);
                            else set.delete(c.key);
                            return {
                              ...prev,
                              attendance_connectors: Array.from(set),
                            };
                          });
                        }}
                      />
                    }
                    label={
                      <Typography variant="body2">
                        {c.vendor} · {c.name}
                        <Typography component="span" variant="caption" color="text.secondary">
                          {" "}
                          ({c.tier})
                        </Typography>
                      </Typography>
                    }
                  />
                );
              })}
            </Box>
          </FormGroup>
        )}

        <FormControlLabel
          control={
            <Checkbox
              checked={form.active}
              disabled={readOnly}
              onChange={(e) => setForm({ ...form, active: e.target.checked })}
            />
          }
          label="Active (visible on pricing)"
        />
      </FormPageShell>
    </PlatformGate>
  );
}
