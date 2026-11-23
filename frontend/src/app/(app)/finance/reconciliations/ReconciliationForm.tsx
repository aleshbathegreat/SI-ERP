"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { todayISO } from "@/components/DateTextField";
import Link from "next/link";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Chip,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import LockIcon from "@mui/icons-material/Lock";
import { useSnackbar } from "notistack";
import FormPageShell from "@/components/crud/FormPageShell";
import { DetailSection } from "@/components/crud/DetailPageShell";
import ModuleGate from "@/components/ModuleGate";
import { useEntityForm, type FormMode } from "@/hooks/useEntityForm";
import { usePermissions } from "@/hooks/usePermissions";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { listResource } from "@/lib/crudApi";
import RelationSelect, { RELATIONS } from "@/components/crud/RelationSelect";

type BankOpt = {
  id: number;
  name: string;
  bank_name: string;
  account_no: string;
  current_balance?: string | number;
  opening_balance?: string | number;
};

type StmtLine = {
  id: number;
  txn_date: string;
  description: string;
  amount: string | number;
  reference?: string;
  matched?: boolean;
};

const MODULE = "finance.banks";
const BASE = "/finance/reconciliations";
const API = "/finance/bank-reconciliations/";

const empty = {
  bank_account: "",
  statement_date: todayISO(),
  statement_balance: "0",
  book_balance: "0",
  status: "open",
  notes: "",
};

function Kpi({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "default" | "ok" | "warn";
}) {
  const color =
    tone === "ok" ? "success.main" : tone === "warn" ? "warning.main" : "text.primary";
  return (
    <Card variant="outlined" sx={{ flex: 1, minWidth: 130 }}>
      <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
        <Typography variant="caption" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="h6" fontWeight={700} color={color}>
          {value}
        </Typography>
      </CardContent>
    </Card>
  );
}

export default function ReconciliationForm({
  mode,
  id,
}: {
  mode: FormMode;
  id?: string;
}) {
  const { canChange } = usePermissions();
  const { enqueueSnackbar } = useSnackbar();
  const [banks, setBanks] = useState<BankOpt[]>([]);
  const [lines, setLines] = useState<StmtLine[]>([]);
  const [uploading, setUploading] = useState(false);
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const { form, setForm, loading, saving, save, reload, readOnly } = useEntityForm({
    resourcePath: API,
    entityLabel: "Bank reconciliation",
    basePath: BASE,
    mode,
    id,
    empty,
    mapLoaded: (row) => ({
      bank_account: String(row.bank_account ?? ""),
      statement_date: String(row.statement_date ?? ""),
      statement_balance: String(row.statement_balance ?? "0"),
      book_balance: String(row.book_balance ?? "0"),
      status: String(row.status ?? "open"),
      notes: String(row.notes ?? ""),
    }),
    mapPayload: (f) => ({
      bank_account: Number(f.bank_account),
      statement_date: f.statement_date || null,
      statement_balance: Number(f.statement_balance) || 0,
      book_balance: Number(f.book_balance) || 0,
      status: f.status,
      notes: f.notes || "",
    }),
  });

  const closed = String(form.status) === "closed";
  const fieldsReadOnly = readOnly || closed;

  useEffect(() => {
    listResource<BankOpt>("/finance/banks/")
      .then((rows) => setBanks(rows.filter((b) => b)))
      .catch(() => undefined);
  }, []);

  const loadLines = async (reconId: string, bankAccountId: string) => {
    try {
      const params: Record<string, string> = {};
      if (reconId) params.reconciliation = reconId;
      else if (bankAccountId) params.bank_account = bankAccountId;
      const { data } = await api.get("/finance/bank-statements/", { params });
      const rows = Array.isArray(data) ? data : data?.results || [];
      setLines(rows as StmtLine[]);
    } catch {
      setLines([]);
    }
  };

  useEffect(() => {
    if (mode === "create") return;
    if (!id) return;
    loadLines(id, String(form.bank_account || "")).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, mode, form.bank_account]);

  const stats = useMemo(() => {
    const stmt = Number(form.statement_balance) || 0;
    const book = Number(form.book_balance) || 0;
    const difference = stmt - book;
    const matched = lines.filter((l) => l.matched).length;
    const unmatched = lines.length - matched;
    const cleared = lines
      .filter((l) => l.matched)
      .reduce((a, l) => a + (Number(l.amount) || 0), 0);
    const outstanding = lines
      .filter((l) => !l.matched)
      .reduce((a, l) => a + (Number(l.amount) || 0), 0);
    return {
      difference,
      matched,
      unmatched,
      cleared,
      outstanding,
      canClose: Math.abs(difference) < 0.01 && unmatched === 0,
    };
  }, [form.statement_balance, form.book_balance, lines]);

  const onBankChange = (bankId: string) => {
    const bank = banks.find((b) => String(b.id) === bankId);
    const book =
      bank?.current_balance != null && bank.current_balance !== ""
        ? String(bank.current_balance)
        : bank?.opening_balance != null
          ? String(bank.opening_balance)
          : form.book_balance;
    setForm({ ...form, bank_account: bankId, book_balance: book });
  };

  const uploadCsv = async (file: File) => {
    if (!id) {
      enqueueSnackbar("Save the reconciliation before uploading a CSV", {
        variant: "warning",
      });
      return;
    }
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await api.post(`${API}${id}/upload-csv/`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const n = data?.created ?? 0;
      enqueueSnackbar(`Imported ${n} statement line${n === 1 ? "" : "s"}`, {
        variant: "success",
      });
      if (Array.isArray(data?.skipped_errors) && data.skipped_errors.length) {
        enqueueSnackbar(data.skipped_errors.slice(0, 3).join("; "), {
          variant: "warning",
        });
      }
      await loadLines(id, String(form.bank_account || ""));
    } catch (e) {
      enqueueSnackbar(getApiErrorMessage(e, "CSV upload failed"), errorSnackbarOpts);
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const toggleMatch = async (line: StmtLine) => {
    if (!canChange(MODULE) || closed) return;
    const next = !line.matched;
    setLines((prev) => prev.map((l) => (l.id === line.id ? { ...l, matched: next } : l)));
    try {
      await api.patch(`/finance/bank-statements/${line.id}/`, { matched: next });
    } catch (e) {
      setLines((prev) =>
        prev.map((l) => (l.id === line.id ? { ...l, matched: line.matched } : l))
      );
      enqueueSnackbar(getApiErrorMessage(e, "Could not update match"), errorSnackbarOpts);
    }
  };

  const runAutoMatch = async () => {
    if (!id) return;
    setBusy(true);
    try {
      const { data } = await api.post("/finance/bank-statements/auto-match/", {
        reconciliation_id: Number(id),
      });
      enqueueSnackbar(
        `Auto-matched ${data?.matched ?? 0} line(s)${
          data?.remaining_unmatched != null
            ? ` · ${data.remaining_unmatched} still open`
            : ""
        }`,
        { variant: "success" }
      );
      await reload();
      await loadLines(id, String(form.bank_account || ""));
    } catch (e) {
      enqueueSnackbar(getApiErrorMessage(e, "Auto-match failed"), errorSnackbarOpts);
    } finally {
      setBusy(false);
    }
  };

  const runClose = async (force = false) => {
    if (!id) return;
    if (!force && !stats.canClose) {
      enqueueSnackbar(
        "Clear the difference and match all lines before closing (or force close).",
        { variant: "warning" }
      );
      return;
    }
    setBusy(true);
    try {
      await api.post(`${API}${id}/close/`, force ? { force: true } : {});
      enqueueSnackbar("Reconciliation closed · bank balance synced", {
        variant: "success",
      });
      await reload();
      await loadLines(id, String(form.bank_account || ""));
    } catch (e) {
      enqueueSnackbar(getApiErrorMessage(e, "Close failed"), errorSnackbarOpts);
    } finally {
      setBusy(false);
    }
  };

  const title =
    mode === "create"
      ? "Match a bank statement"
      : mode === "edit"
        ? "Edit statement match"
        : "Bank statement";

  return (
    <ModuleGate module={MODULE}>
      <FormPageShell
        title={title}
        subtitle="Enter the statement date and ending balance, then tick the lines that appear on it."
        backHref={BASE}
        mode={fieldsReadOnly && mode !== "create" ? "view" : mode}
        loading={loading}
        saving={saving}
        onSubmit={save}
        submitLabel="Save and close"
        extraActions={
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {mode !== "create" && id && canChange(MODULE) && !closed ? (
              <>
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={<AutoFixHighIcon />}
                  disabled={busy || lines.length === 0}
                  onClick={runAutoMatch}
                >
                  Auto-match
                </Button>
                <Button
                  size="small"
                  variant="contained"
                  color="secondary"
                  startIcon={<LockIcon />}
                  disabled={busy}
                  onClick={() => runClose(false)}
                >
                  Close
                </Button>
                {!stats.canClose ? (
                  <Button
                    size="small"
                    color="warning"
                    variant="outlined"
                    disabled={busy}
                    onClick={() => runClose(true)}
                  >
                    Force close
                  </Button>
                ) : null}
              </>
            ) : null}
            {mode === "view" && canChange(MODULE) && id && !closed ? (
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
        <Stack spacing={2}>
          {mode !== "create" ? (
            <Stack direction="row" spacing={1.5} flexWrap="wrap" useFlexGap>
              <Kpi
                label="Difference"
                value={stats.difference.toFixed(2)}
                tone={Math.abs(stats.difference) < 0.01 ? "ok" : "warn"}
              />
              <Kpi label="Matched" value={`${stats.matched}/${lines.length}`} />
              <Kpi
                label="Unmatched"
                value={String(stats.unmatched)}
                tone={stats.unmatched === 0 ? "ok" : "warn"}
              />
              <Kpi label="Cleared sum" value={stats.cleared.toFixed(2)} />
              <Kpi label="Outstanding" value={stats.outstanding.toFixed(2)} />
            </Stack>
          ) : null}

          {closed ? (
            <Alert severity="success">
              Closed — bank current balance and last reconciled date were synced from this
              statement.
            </Alert>
          ) : mode !== "create" && !stats.canClose ? (
            <Alert severity="info">
              Match every statement line and bring statement vs book difference to zero before
              closing (enterprise close gate).
            </Alert>
          ) : null}

          <DetailSection title="Reconciliation" defaultExpanded>
            <Stack spacing={2}>
              <Stack direction="row" spacing={1} alignItems="center">
                <Typography variant="body2" color="text.secondary">
                  Status
                </Typography>
                <Chip
                  size="small"
                  color={
                    form.status === "closed"
                      ? "success"
                      : form.status === "matched"
                        ? "info"
                        : "default"
                  }
                  label={String(form.status)}
                />
              </Stack>
              <RelationSelect
                label="Bank account"
                required
                value={form.bank_account}
                disabled={fieldsReadOnly}
                relation={RELATIONS.bankAccount}
                onChange={(v) => onBankChange(v)}
              />
              <TextField
                label="Statement date"
                type="date"
                required
                fullWidth
                InputLabelProps={{ shrink: true }}
                value={form.statement_date}
                disabled={fieldsReadOnly}
                onChange={(e) => setForm({ ...form, statement_date: e.target.value })}
              />
              <TextField
                label="Balance on the statement"
                helperText="The ending balance the bank printed."
                type="number"
                fullWidth
                value={form.statement_balance}
                disabled={fieldsReadOnly}
                onChange={(e) =>
                  setForm({ ...form, statement_balance: e.target.value })
                }
              />
              <TextField
                label="Balance in your books"
                type="number"
                fullWidth
                value={form.book_balance}
                disabled={fieldsReadOnly}
                helperText="Starts from the balance already stored for this bank."
                onChange={(e) => setForm({ ...form, book_balance: e.target.value })}
              />
              <TextField
                label="Notes"
                multiline
                minRows={2}
                fullWidth
                value={form.notes}
                disabled={fieldsReadOnly}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
              />
            </Stack>
          </DetailSection>

          {mode !== "create" && id ? (
            <DetailSection
              title="Statement workspace"
              description="Tick to match / unmatch. CSV headers: date, description, amount (or debit/credit), reference"
              defaultExpanded
              action={
                canChange(MODULE) && !closed ? (
                  <Stack direction="row" spacing={1}>
                    <input
                      ref={fileRef}
                      type="file"
                      accept=".csv,text/csv"
                      hidden
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (f) uploadCsv(f);
                      }}
                    />
                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={<UploadFileIcon />}
                      disabled={uploading}
                      onClick={() => fileRef.current?.click()}
                    >
                      {uploading ? "Uploading…" : "Upload CSV"}
                    </Button>
                  </Stack>
                ) : null
              }
            >
              <Box sx={{ overflowX: "auto" }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell padding="checkbox">Match</TableCell>
                      <TableCell>Date</TableCell>
                      <TableCell>Description</TableCell>
                      <TableCell>Reference</TableCell>
                      <TableCell align="right">Amount</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {lines.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5}>
                          <Typography variant="body2" color="text.secondary">
                            No statement lines yet. Upload a CSV to import.
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ) : (
                      lines.map((l) => (
                        <TableRow
                          key={l.id}
                          hover
                          selected={!!l.matched}
                          sx={{
                            bgcolor: l.matched ? "action.selected" : undefined,
                          }}
                        >
                          <TableCell padding="checkbox">
                            <Checkbox
                              checked={!!l.matched}
                              disabled={!canChange(MODULE) || closed}
                              onChange={() => toggleMatch(l)}
                            />
                          </TableCell>
                          <TableCell>{l.txn_date}</TableCell>
                          <TableCell>{l.description || "—"}</TableCell>
                          <TableCell>{l.reference || "—"}</TableCell>
                          <TableCell align="right">{Number(l.amount).toFixed(2)}</TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </Box>
            </DetailSection>
          ) : (
            <Typography variant="body2" color="text.secondary">
              Save the reconciliation first, then upload a bank statement CSV and match lines.
            </Typography>
          )}
        </Stack>
      </FormPageShell>
    </ModuleGate>
  );
}
