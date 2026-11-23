"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import {
  Alert,
  Box,
  Button,
  Chip,
  IconButton,
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
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlined";
import EditIcon from "@mui/icons-material/Edit";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import { useParams, useRouter } from "next/navigation";
import { useSnackbar } from "notistack";
import FormPageShell from "@/components/crud/FormPageShell";
import RelationSelect, { RELATIONS } from "@/components/crud/RelationSelect";
import ModuleGate from "@/components/ModuleGate";
import WorkflowActions from "@/components/WorkflowActions";
import { useEntityForm, type FormMode } from "@/hooks/useEntityForm";
import { usePermissions } from "@/hooks/usePermissions";
import { createResource } from "@/lib/crudApi";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { rejectNegative } from "@/lib/numberBounds";

type Line = {
  account: string;
  cost_center: string;
  cost_center_label: string;
  debit: string;
  credit: string;
  description: string;
};

const emptyLine = (): Line => ({
  account: "",
  cost_center: "",
  cost_center_label: "",
  debit: "",
  credit: "",
  description: "",
});

const moduleKey = "finance.journals";
const basePath = "/finance/journals";
const resourcePath = "/finance/journals/";

const empty = {
  entry_date: todayISO(),
  reference: "",
  narration: "",
  status: "draft",
  lines: [emptyLine(), emptyLine()] as Line[],
};

const STATUS_HELP: Record<string, string> = {
  draft: "Draft — not in the books yet",
  submitted: "Waiting for approval",
  approved: "Approved",
  posted: "Posted",
  rejected: "Sent back",
};

const statusColor = (s: string): "default" | "info" | "warning" | "success" | "error" => {
  if (s === "draft") return "default";
  if (s === "submitted") return "info";
  if (s === "approved") return "warning";
  if (s === "posted") return "success";
  if (s === "rejected") return "error";
  return "default";
};

function money(n: number) {
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function usableLines(lines: Line[]) {
  return lines.filter((l) => Number(l.debit) > 0 || Number(l.credit) > 0);
}

export default function JournalForm({ mode }: { mode: FormMode }) {
  const params = useParams();
  const id = mode === "create" ? undefined : String(params.id);
  const router = useRouter();
  const { enqueueSnackbar } = useSnackbar();
  const { canAdd, canChange } = usePermissions();
  const [savingNew, setSavingNew] = useState(false);

  const { form, setForm, loading, saving, save, reload, readOnly } = useEntityForm({
    resourcePath,
    entityLabel: "Journal entry",
    basePath,
    mode,
    id,
    empty,
    mapLoaded: (row) => ({
      entry_date: String(row.entry_date ?? empty.entry_date),
      reference: String(row.reference ?? ""),
      narration: String(row.narration ?? ""),
      status: String(row.status ?? "draft"),
      lines: Array.isArray(row.lines) && row.lines.length
        ? (row.lines as Record<string, unknown>[]).map((l) => ({
            account: l.account != null ? String(l.account) : "",
            cost_center: l.cost_center != null ? String(l.cost_center) : "",
            cost_center_label: String(l.cost_center_label ?? ""),
            debit: Number(l.debit) ? String(l.debit) : "",
            credit: Number(l.credit) ? String(l.credit) : "",
            description: String(l.description ?? ""),
          }))
        : [emptyLine(), emptyLine()],
    }),
    mapPayload: (f) => ({
      entry_date: f.entry_date,
      reference: f.reference,
      narration: f.narration,
      lines: usableLines(f.lines as Line[]).map((l) => ({
        account: Number(l.account),
        cost_center: l.cost_center ? Number(l.cost_center) : null,
        debit: Number(l.debit) || 0,
        credit: Number(l.credit) || 0,
        description: l.description || "",
      })),
    }),
  });

  const lines = (form.lines as Line[]) || [];
  const totals = useMemo(() => {
    const debit = lines.reduce((a, l) => a + (Number(l.debit) || 0), 0);
    const credit = lines.reduce((a, l) => a + (Number(l.credit) || 0), 0);
    return { debit, credit, balanced: Math.abs(debit - credit) < 0.005 && debit > 0 };
  }, [lines]);

  const status = String(form.status || "draft");
  const editableStatus = status === "draft" || status === "rejected";
  const locked = mode !== "create" && !editableStatus;
  const fieldsReadOnly = readOnly || locked;

  const setLine = (idx: number, patch: Partial<Line>) => {
    if (fieldsReadOnly) return;
    setForm({
      ...form,
      lines: lines.map((l, i) => (i === idx ? { ...l, ...patch } : l)),
    });
  };

  const lineError = () => {
    const kept = usableLines(lines);
    if (kept.length < 2) return "Add at least two lines, one debit and one credit.";
    if (kept.some((l) => !l.account)) return "Choose an account on every line that has an amount.";
    if (kept.some((l) => Number(l.debit) > 0 && Number(l.credit) > 0)) {
      return "A line is either a debit or a credit.";
    }
    if (!totals.balanced) {
      return `Debits ${money(totals.debit)} and credits ${money(totals.credit)} must be equal.`;
    }
    return null;
  };

  const payloadLines = () =>
    usableLines(lines).map((l) => ({
      account: Number(l.account),
      cost_center: l.cost_center ? Number(l.cost_center) : null,
      debit: Number(l.debit) || 0,
      credit: Number(l.credit) || 0,
      description: l.description || "",
    }));

  const handleSave = async () => {
    const message = lineError();
    if (message) {
      enqueueSnackbar(message, { variant: "warning" });
      return;
    }
    await save();
  };

  const saveAndNew = async () => {
    if (mode !== "create" || savingNew) return;
    const message = lineError();
    if (message) {
      enqueueSnackbar(message, { variant: "warning" });
      return;
    }
    setSavingNew(true);
    try {
      await createResource(resourcePath, {
        entry_date: form.entry_date,
        reference: form.reference,
        narration: form.narration,
        lines: payloadLines(),
      });
      enqueueSnackbar("Saved. Ready for the next one.", { variant: "success" });
      setForm({ ...empty, entry_date: todayISO(), lines: [emptyLine(), emptyLine()] });
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Could not save the journal entry"), errorSnackbarOpts);
    } finally {
      setSavingNew(false);
    }
  };

  const clearForm = () => {
    setForm({ ...empty, entry_date: form.entry_date || todayISO(), lines: [emptyLine(), emptyLine()] });
  };

  const duplicateAsDraft = async () => {
    if (!canAdd(moduleKey)) return;
    try {
      const created = (await createResource(resourcePath, {
        entry_date: form.entry_date,
        reference: form.reference ? `${form.reference} (copy)` : "",
        narration: form.narration,
        lines: payloadLines(),
      })) as { id?: number };
      enqueueSnackbar("Draft copy created", { variant: "success" });
      if (created?.id) router.push(`${basePath}/${created.id}/edit`);
      else router.push(basePath);
    } catch (e) {
      enqueueSnackbar(getApiErrorMessage(e, "Could not duplicate"), errorSnackbarOpts);
    }
  };

  const reversePosted = async () => {
    if (!id || status !== "posted" || !canChange(moduleKey)) return;
    if (
      !window.confirm(
        "Post a reversing journal (swap debit and credit)? The original stays posted."
      )
    ) {
      return;
    }
    try {
      const { data } = await api.post(`${resourcePath}${id}/reverse/`);
      const rev = data?.reversal;
      enqueueSnackbar(rev?.reference ? `Reversal ${rev.reference} posted` : "Reversal posted", {
        variant: "success",
      });
      if (rev?.id) router.push(`${basePath}/${rev.id}`);
      else await reload();
    } catch (e) {
      enqueueSnackbar(getApiErrorMessage(e, "Reverse failed"), errorSnackbarOpts);
    }
  };

  const fillDifference = () => {
    const gap = Number((totals.debit - totals.credit).toFixed(2));
    if (!gap) return;
    setForm({
      ...form,
      lines: [
        ...lines,
        {
          ...emptyLine(),
          debit: gap < 0 ? Math.abs(gap).toFixed(2) : "",
          credit: gap > 0 ? gap.toFixed(2) : "",
        },
      ],
    });
  };

  const title = mode === "edit" ? "Edit journal entry" : "Journal entry";

  return (
    <ModuleGate module={moduleKey}>
      <FormPageShell
        title={title}
        subtitle="Enter each account on its own line. Debits and credits must be equal before you save."
        backHref={basePath}
        mode={fieldsReadOnly && mode !== "create" ? "view" : mode}
        loading={loading}
        saving={saving || savingNew}
        onSubmit={handleSave}
        submitLabel="Save and close"
        maxWidth={1100}
        extraActions={
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {mode === "create" && !fieldsReadOnly ? (
              <>
                <Button size="small" variant="text" disabled={saving || savingNew} onClick={clearForm}>
                  Clear
                </Button>
                <Button size="small" variant="outlined" disabled={saving || savingNew} onClick={saveAndNew}>
                  Save and new
                </Button>
              </>
            ) : null}
            {id ? (
              <WorkflowActions
                resourcePath={resourcePath}
                id={Number(id)}
                status={status}
                moduleKey={moduleKey}
                allowPost
                onDone={reload}
              />
            ) : null}
            {id && canAdd(moduleKey) ? (
              <Button size="small" variant="outlined" startIcon={<ContentCopyIcon />} onClick={duplicateAsDraft}>
                Duplicate
              </Button>
            ) : null}
            {id && status === "posted" && canChange(moduleKey) ? (
              <Button size="small" color="warning" variant="outlined" onClick={reversePosted}>
                Reverse
              </Button>
            ) : null}
            {mode === "view" && canChange(moduleKey) && id && editableStatus ? (
              <Button component={Link} href={`${basePath}/${id}/edit`} variant="contained" startIcon={<EditIcon />}>
                Edit
              </Button>
            ) : null}
          </Stack>
        }
      >
        <Stack spacing={2}>
          {locked ? (
            <Alert severity={status === "posted" ? "success" : "info"}>
              This journal entry is {STATUS_HELP[status] || status}. The lines stay locked.
            </Alert>
          ) : null}

          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="body2" color="text.secondary">
              Status
            </Typography>
            <Chip size="small" color={statusColor(status)} label={STATUS_HELP[status] || status} />
          </Stack>

          <Box
            sx={{
              display: "grid",
              gap: 2,
              gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
              maxWidth: 640,
            }}
          >
            <DateTextField
              label="Journal date"
              required
              value={form.entry_date}
              disabled={fieldsReadOnly}
              onChange={(e) => setForm({ ...form, entry_date: e.target.value })}
            />
            <TextField
              label="Journal no."
              fullWidth
              value={form.reference}
              disabled={fieldsReadOnly}
              placeholder="Auto"
              helperText="Leave blank and a number is assigned."
              onChange={(e) => setForm({ ...form, reference: e.target.value })}
            />
          </Box>

          <Box sx={{ overflowX: "auto", border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
            <Table size="small" sx={{ minWidth: 880 }}>
              <TableHead>
                <TableRow sx={{ bgcolor: "action.hover" }}>
                  <TableCell width={36}>#</TableCell>
                  <TableCell sx={{ minWidth: 220 }}>Account</TableCell>
                  <TableCell align="right" sx={{ minWidth: 130 }}>
                    Debits
                  </TableCell>
                  <TableCell align="right" sx={{ minWidth: 130 }}>
                    Credits
                  </TableCell>
                  <TableCell sx={{ minWidth: 180 }}>Description</TableCell>
                  <TableCell sx={{ minWidth: 160 }}>Class</TableCell>
                  <TableCell width={40} />
                </TableRow>
              </TableHead>
              <TableBody>
                {lines.map((line, idx) => (
                  <TableRow key={idx} hover>
                    <TableCell>{idx + 1}</TableCell>
                    <TableCell>
                      <RelationSelect
                        label="Account"
                        required
                        size="small"
                        value={line.account}
                        disabled={fieldsReadOnly}
                        relation={RELATIONS.account}
                        onChange={(v) => setLine(idx, { account: v })}
                      />
                    </TableCell>
                    <TableCell align="right">
                      <TextField
                        size="small"
                        type="number"
                        placeholder="0.00"
                        value={line.debit}
                        disabled={fieldsReadOnly}
                        slotProps={{ htmlInput: { min: 0, step: "0.01", style: { textAlign: "right" } } }}
                        onChange={(e) => {
                          const next = rejectNegative(e.target.value, { min: 0 });
                          if (next == null) return;
                          setLine(idx, { debit: next, credit: next ? "" : line.credit });
                        }}
                      />
                    </TableCell>
                    <TableCell align="right">
                      <TextField
                        size="small"
                        type="number"
                        placeholder="0.00"
                        value={line.credit}
                        disabled={fieldsReadOnly}
                        slotProps={{ htmlInput: { min: 0, step: "0.01", style: { textAlign: "right" } } }}
                        onChange={(e) => {
                          const next = rejectNegative(e.target.value, { min: 0 });
                          if (next == null) return;
                          setLine(idx, { credit: next, debit: next ? "" : line.debit });
                        }}
                      />
                    </TableCell>
                    <TableCell>
                      <TextField
                        size="small"
                        fullWidth
                        placeholder="Description"
                        value={line.description}
                        disabled={fieldsReadOnly}
                        onChange={(e) => setLine(idx, { description: e.target.value })}
                      />
                    </TableCell>
                    <TableCell>
                      <RelationSelect
                        label="Class"
                        size="small"
                        value={line.cost_center}
                        fallbackLabel={line.cost_center_label}
                        disabled={fieldsReadOnly}
                        relation={RELATIONS.costCenter}
                        onChange={(v) => setLine(idx, { cost_center: v, cost_center_label: "" })}
                      />
                    </TableCell>
                    <TableCell>
                      {!fieldsReadOnly ? (
                        <IconButton
                          aria-label="Remove line"
                          size="small"
                          disabled={lines.length <= 2}
                          onClick={() => setForm({ ...form, lines: lines.filter((_, i) => i !== idx) })}
                        >
                          <DeleteOutlineIcon fontSize="small" />
                        </IconButton>
                      ) : null}
                    </TableCell>
                  </TableRow>
                ))}
                <TableRow>
                  <TableCell colSpan={2} sx={{ borderBottom: 0 }}>
                    <Typography variant="subtitle2">Totals</Typography>
                  </TableCell>
                  <TableCell align="right" sx={{ borderBottom: 0, fontWeight: 700 }}>
                    {money(totals.debit)}
                  </TableCell>
                  <TableCell align="right" sx={{ borderBottom: 0, fontWeight: 700 }}>
                    {money(totals.credit)}
                  </TableCell>
                  <TableCell colSpan={3} sx={{ borderBottom: 0 }}>
                    {totals.debit > 0 || totals.credit > 0 ? (
                      <Typography
                        variant="body2"
                        color={totals.balanced ? "success.main" : "warning.dark"}
                        fontWeight={600}
                      >
                        {totals.balanced
                          ? "Balanced"
                          : `Out of balance by ${money(Math.abs(totals.debit - totals.credit))}`}
                      </Typography>
                    ) : null}
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </Box>

          {!fieldsReadOnly ? (
            <Stack direction="row" spacing={1}>
              <Button
                size="small"
                startIcon={<AddIcon />}
                onClick={() => setForm({ ...form, lines: [...lines, emptyLine(), emptyLine()] })}
              >
                Add lines
              </Button>
              {!totals.balanced && (totals.debit > 0 || totals.credit > 0) ? (
                <Button size="small" onClick={fillDifference}>
                  Add the difference
                </Button>
              ) : null}
            </Stack>
          ) : null}

          <TextField
            label="Memo"
            multiline
            minRows={2}
            fullWidth
            value={form.narration}
            disabled={fieldsReadOnly}
            placeholder="What this journal entry is for"
            onChange={(e) => setForm({ ...form, narration: e.target.value })}
          />
        </Stack>
      </FormPageShell>
    </ModuleGate>
  );
}
