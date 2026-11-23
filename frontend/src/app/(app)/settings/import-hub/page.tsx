"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  MenuItem,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import DownloadIcon from "@mui/icons-material/Download";
import ArchiveIcon from "@mui/icons-material/Archive";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import PageHeader from "@/components/PageHeader";
import ModuleGate from "@/components/ModuleGate";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { useSnackbar } from "notistack";

type ColumnSpec = {
  name: string;
  required: boolean;
  example?: string;
  help?: string;
};

type EntitySpec = {
  key: string;
  label: string;
  description: string;
  module: string;
  columns: ColumnSpec[];
};

type EntityResult = {
  entity?: string;
  label?: string;
  source_file?: string;
  row_count?: number;
  created?: number;
  updated?: number;
  skipped?: number;
  error_count?: number;
  warning_count?: number;
  errors?: { row: number; message: string }[];
  warnings?: { row: number; message: string }[];
  preview_rows?: Record<string, unknown>[];
};

type ImportResult = {
  mode?: string;
  entity?: string;
  label?: string;
  filename?: string;
  message?: string;
  dry_run?: boolean;
  row_count?: number;
  created?: number;
  updated?: number;
  skipped?: number;
  error_count?: number;
  warning_count?: number;
  file_count?: number;
  entities_processed?: string[];
  entities_missing?: string[];
  skipped_files?: string[];
  filename_headers?: string[];
  expected_columns?: string[];
  errors?: { row: number; message: string }[];
  warnings?: { row: number; message: string }[];
  preview_rows?: Record<string, unknown>[];
  results?: EntityResult[];
};

type UploadMode = "csv" | "zip";

export default function ImportHubPage() {
  const { enqueueSnackbar } = useSnackbar();
  const [entities, setEntities] = useState<EntitySpec[]>([]);
  const [entity, setEntity] = useState("");
  const [mode, setMode] = useState<UploadMode>("csv");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [loadError, setLoadError] = useState("");

  const selected = useMemo(
    () => entities.find((e) => e.key === entity) || null,
    [entities, entity]
  );

  const loadCatalog = useCallback(async () => {
    try {
      const { data } = await api.get("/settings/import-hub/catalog/");
      const list = (data.entities || []) as EntitySpec[];
      setEntities(list);
      if (list.length && !entity) setEntity(list[0].key);
      setLoadError("");
    } catch (e: unknown) {
      setLoadError(getApiErrorMessage(e, "Could not load import catalog"));
    }
  }, [entity]);

  useEffect(() => {
    loadCatalog();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const saveBlob = (data: BlobPart, filename: string, mime: string) => {
    const blob = new Blob([data], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadTemplate = async () => {
    if (!entity) return;
    try {
      const res = await api.get(`/settings/import-hub/templates/${entity}/`, {
        responseType: "blob",
      });
      saveBlob(res.data, `import_${entity}_template.csv`, "text/csv;charset=utf-8");
      enqueueSnackbar("Template downloaded", { variant: "success" });
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Template download failed"), errorSnackbarOpts);
    }
  };

  const downloadAllTemplates = async () => {
    try {
      setBusy(true);
      const res = await api.get("/settings/import-hub/templates-pack/", {
        responseType: "blob",
      });
      saveBlob(res.data, "sierp_import_templates.zip", "application/zip");
      enqueueSnackbar("All templates downloaded (ZIP)", { variant: "success" });
    } catch (e: unknown) {
      enqueueSnackbar(
        getApiErrorMessage(e, "Could not download template pack"),
        errorSnackbarOpts
      );
    } finally {
      setBusy(false);
    }
  };

  const run = async (action: "preview" | "commit") => {
    if (!file) {
      enqueueSnackbar(
        mode === "zip" ? "Choose a ZIP pack first" : "Choose a CSV file first",
        { variant: "warning" }
      );
      return;
    }
    if (mode === "csv" && !entity) {
      enqueueSnackbar("Select an entity for single-CSV import", { variant: "warning" });
      return;
    }
    setBusy(true);
    setResult(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      if (mode === "csv") fd.append("entity", entity);
      if (action === "commit") fd.append("confirm", "true");
      const path =
        mode === "zip"
          ? action === "preview"
            ? "/settings/import-hub/preview-pack/"
            : "/settings/import-hub/commit-pack/"
          : action === "preview"
            ? "/settings/import-hub/preview/"
            : "/settings/import-hub/commit/";
      const { data } = await api.post(path, fd, {
        headers: { "Content-Type": "multipart/form-data" },
        validateStatus: (s) => (s >= 200 && s < 300) || s === 207,
      });
      setResult(data as ImportResult);
      enqueueSnackbar(
        action === "preview" ? "Dry-run ready" : "Import committed",
        {
          variant:
            action === "commit" && (data.error_count || 0) > 0 ? "warning" : "success",
        }
      );
    } catch (e: unknown) {
      enqueueSnackbar(
        getApiErrorMessage(e, action === "preview" ? "Preview failed" : "Import failed"),
        errorSnackbarOpts
      );
    } finally {
      setBusy(false);
    }
  };

  const canCommit =
    !!file &&
    !!result &&
    result.dry_run === true &&
    (result.error_count || 0) === 0 &&
    (mode === "zip" || !!entity);

  const packResults = result?.results || [];

  return (
    <ModuleGate module="settings.import_hub">
      <PageHeader
        title="Data import hub"
        subtitle="Templates, single CSV, or full ZIP pack — validate then commit in dependency order"
        moduleKey="settings.import_hub"
      />
      <Stack spacing={2}>
        {loadError ? <Alert severity="error">{loadError}</Alert> : null}

        <Card>
          <CardContent>
            <Stack spacing={2}>
              <Typography variant="subtitle1" fontWeight={700}>
                1 · Templates
              </Typography>
              <TextField
                select
                label="Entity (for single CSV)"
                value={entity}
                onChange={(e) => {
                  setEntity(e.target.value);
                  setResult(null);
                  if (mode === "csv") setFile(null);
                }}
                fullWidth
                helperText={selected?.description || " "}
              >
                {entities.map((e) => (
                  <MenuItem key={e.key} value={e.key}>
                    {e.label}
                  </MenuItem>
                ))}
              </TextField>

              {selected ? (
                <Box>
                  <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }} flexWrap="wrap" useFlexGap>
                    <Typography variant="body2" color="text.secondary">
                      Required
                    </Typography>
                    {selected.columns
                      .filter((c) => c.required)
                      .map((c) => (
                        <Chip key={c.name} size="small" label={c.name} color="primary" />
                      ))}
                  </Stack>
                </Box>
              ) : null}

              <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
                <Button
                  variant="outlined"
                  startIcon={<DownloadIcon />}
                  onClick={downloadTemplate}
                  disabled={!entity || busy}
                >
                  Download template
                </Button>
                <Button
                  variant="contained"
                  startIcon={<ArchiveIcon />}
                  onClick={downloadAllTemplates}
                  disabled={busy || entities.length === 0}
                >
                  Download all templates
                </Button>
              </Stack>
              <Typography variant="caption" color="text.secondary">
                ZIP pack: 00_README.txt (order guide), numbered CSVs, manifest.csv — UTF-8
                for Excel. Fill the CSVs, then upload the same ZIP below.
              </Typography>
            </Stack>
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <Stack spacing={2}>
              <Typography variant="subtitle1" fontWeight={700}>
                2 · Upload &amp; import
              </Typography>
              <ToggleButtonGroup
                exclusive
                size="small"
                value={mode}
                onChange={(_, v: UploadMode | null) => {
                  if (!v) return;
                  setMode(v);
                  setFile(null);
                  setResult(null);
                }}
              >
                <ToggleButton value="csv">Single CSV</ToggleButton>
                <ToggleButton value="zip">ZIP pack (all)</ToggleButton>
              </ToggleButtonGroup>

              <Button
                variant="contained"
                component="label"
                startIcon={<UploadFileIcon />}
                disabled={busy || (mode === "csv" && !entity)}
                sx={{ alignSelf: "flex-start" }}
              >
                {file
                  ? file.name
                  : mode === "zip"
                    ? "Choose ZIP pack"
                    : "Choose CSV file"}
                <input
                  type="file"
                  accept={
                    mode === "zip"
                      ? ".zip,application/zip"
                      : ".csv,text/csv"
                  }
                  hidden
                  onChange={(e) => {
                    setFile(e.target.files?.[0] || null);
                    setResult(null);
                  }}
                />
              </Button>

              <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
                <Button
                  variant="outlined"
                  onClick={() => run("preview")}
                  disabled={busy || !file || (mode === "csv" && !entity)}
                >
                  {busy ? "Working…" : "Validate (dry-run)"}
                </Button>
                <Button
                  variant="contained"
                  color="success"
                  startIcon={<CheckCircleIcon />}
                  onClick={() => run("commit")}
                  disabled={busy || !canCommit}
                >
                  {mode === "zip" ? "Commit ZIP import" : "Commit import"}
                </Button>
              </Stack>
              <Typography variant="caption" color="text.secondary">
                {mode === "zip"
                  ? "ZIP is processed in recommended order (CoA → cost centers → tax → HR → warehouses → vendors/customers → items → employees → leave → assets → opening journals → CRM → projects). Unrecognized CSVs are skipped."
                  : "Commit stays disabled until a clean dry-run (zero errors)."}
              </Typography>
            </Stack>
          </CardContent>
        </Card>

        {result ? (
          <Card>
            <CardContent>
              <Stack spacing={1.5}>
                <Typography variant="subtitle1" fontWeight={700}>
                  3 · Result
                </Typography>
                <Alert severity={(result.error_count || 0) > 0 ? "warning" : "info"}>
                  {result.message || "Done"}
                  {result.filename ? ` · File: ${result.filename}` : ""}
                </Alert>
                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                  {result.mode === "zip_pack" ? (
                    <Chip label={`Files ${result.file_count ?? packResults.length}`} />
                  ) : null}
                  <Chip label={`Rows ${result.row_count ?? 0}`} />
                  <Chip
                    color="success"
                    variant="outlined"
                    label={`Created ${result.created ?? 0}`}
                  />
                  <Chip
                    color="info"
                    variant="outlined"
                    label={`Updated ${result.updated ?? 0}`}
                  />
                  <Chip label={`Skipped ${result.skipped ?? 0}`} />
                  <Chip
                    color={(result.error_count || 0) > 0 ? "error" : "default"}
                    label={`Errors ${result.error_count ?? 0}`}
                  />
                  <Chip
                    color={(result.warning_count || 0) > 0 ? "warning" : "default"}
                    label={`Warnings ${result.warning_count ?? 0}`}
                  />
                  {result.dry_run ? <Chip label="Dry-run" color="secondary" /> : null}
                </Stack>

                {packResults.length > 0 ? (
                  <Box>
                    <Typography variant="subtitle2" gutterBottom>
                      Per-entity summary
                    </Typography>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Entity</TableCell>
                          <TableCell>Source</TableCell>
                          <TableCell align="right">Rows</TableCell>
                          <TableCell align="right">Created</TableCell>
                          <TableCell align="right">Updated</TableCell>
                          <TableCell align="right">Errors</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {packResults.map((r) => (
                          <TableRow key={`${r.entity}-${r.source_file}`}>
                            <TableCell>{r.label || r.entity}</TableCell>
                            <TableCell>{r.source_file}</TableCell>
                            <TableCell align="right">{r.row_count ?? 0}</TableCell>
                            <TableCell align="right">{r.created ?? 0}</TableCell>
                            <TableCell align="right">{r.updated ?? 0}</TableCell>
                            <TableCell align="right">{r.error_count ?? 0}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </Box>
                ) : null}

                {(result.entities_missing || []).length > 0 ? (
                  <Typography variant="caption" color="text.secondary">
                    Not in ZIP (optional): {(result.entities_missing || []).join(", ")}
                  </Typography>
                ) : null}

                {(result.errors || []).length > 0 ? (
                  <Box>
                    <Typography variant="subtitle2" gutterBottom>
                      Errors
                    </Typography>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell width={80}>Row</TableCell>
                          <TableCell>Message</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {(result.errors || []).slice(0, 50).map((err, idx) => (
                          <TableRow key={`${err.row}-${idx}`}>
                            <TableCell>{err.row}</TableCell>
                            <TableCell>{err.message}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </Box>
                ) : null}

                {packResults.some((r) => (r.errors || []).length > 0) ? (
                  <Box>
                    <Typography variant="subtitle2" gutterBottom>
                      Pack errors (by entity)
                    </Typography>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Entity</TableCell>
                          <TableCell width={80}>Row</TableCell>
                          <TableCell>Message</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {packResults.flatMap((r) =>
                          (r.errors || []).slice(0, 20).map((err, idx) => (
                            <TableRow key={`${r.entity}-${err.row}-${idx}`}>
                              <TableCell>{r.entity}</TableCell>
                              <TableCell>{err.row}</TableCell>
                              <TableCell>{err.message}</TableCell>
                            </TableRow>
                          ))
                        )}
                      </TableBody>
                    </Table>
                  </Box>
                ) : null}

                {(result.preview_rows || []).length > 0 ? (
                  <Box>
                    <Typography variant="subtitle2" gutterBottom>
                      Preview (first rows)
                    </Typography>
                    <Box sx={{ overflowX: "auto" }}>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            {Object.keys(result.preview_rows![0]).map((k) => (
                              <TableCell key={k}>{k}</TableCell>
                            ))}
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {result.preview_rows!.slice(0, 15).map((row, idx) => (
                            <TableRow key={idx}>
                              {Object.keys(result.preview_rows![0]).map((k) => (
                                <TableCell key={k}>{String(row[k] ?? "")}</TableCell>
                              ))}
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </Box>
                  </Box>
                ) : null}
              </Stack>
            </CardContent>
          </Card>
        ) : null}
      </Stack>
    </ModuleGate>
  );
}
