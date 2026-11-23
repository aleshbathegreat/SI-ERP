"use client";

import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import DateTextField from "@/components/DateTextField";
import EssSection, { EssPanel, EssStatusChip } from "@/components/ess/EssSection";
import { EssClaim, fetchEssClaims, submitEssClaim } from "@/lib/essApi";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { useSnackbar } from "notistack";

const CATEGORIES = ["travel", "meal", "medical", "supplies", "general", "other"];

export default function EssClaimsPage() {
  const { enqueueSnackbar } = useSnackbar();
  const [claims, setClaims] = useState<EssClaim[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");
  const [form, setForm] = useState({
    claim_date: "",
    category: "general",
    amount: "",
    notes: "",
  });

  const load = async () => {
    setLoading(true);
    setErr("");
    try {
      setClaims(await fetchEssClaims());
    } catch (e: unknown) {
      setErr(getApiErrorMessage(e, "Could not load claims"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const submit = async () => {
    setSaving(true);
    try {
      await submitEssClaim({
        claim_date: form.claim_date,
        category: form.category,
        amount: form.amount,
        notes: form.notes,
        status: "submitted",
      });
      enqueueSnackbar("Claim submitted", { variant: "success" });
      setForm({ claim_date: "", category: "general", amount: "", notes: "" });
      await load();
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Could not submit claim"), errorSnackbarOpts);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: "grid", placeItems: "center", minHeight: 240 }}>
        <CircularProgress size={32} />
      </Box>
    );
  }

  return (
    <EssSection title="Expense claims" subtitle="Submit and track reimbursements.">
      {err ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {err}
        </Alert>
      ) : null}

      <Box
        sx={{
          display: "grid",
          gap: 2,
          gridTemplateColumns: { xs: "1fr", md: "1fr 1.1fr" },
        }}
      >
        <EssPanel>
          <Typography fontWeight={700} sx={{ mb: 1.5 }}>
            New claim
          </Typography>
          <Stack spacing={1.5}>
            <DateTextField
              label="Claim date"
              value={form.claim_date}
              showFormatHint
              onChange={(e) => setForm({ ...form, claim_date: e.target.value })}
            />
            <TextField
              select
              label="Category"
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
            >
              {CATEGORIES.map((c) => (
                <MenuItem key={c} value={c}>
                  {c}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="Amount"
              type="number"
              value={form.amount}
              onChange={(e) => setForm({ ...form, amount: e.target.value })}
            />
            <TextField
              label="Notes"
              multiline
              minRows={2}
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
            />
            <Button
              variant="contained"
              disabled={saving || !form.claim_date || !form.amount}
              onClick={submit}
            >
              {saving ? "Submitting…" : "Submit claim"}
            </Button>
          </Stack>
        </EssPanel>

        <EssPanel>
          <Typography fontWeight={700} sx={{ mb: 1.5 }}>
            My claims
          </Typography>
          <Stack spacing={1}>
            {claims.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No claims yet.
              </Typography>
            ) : (
              claims.map((c) => (
                <Box
                  key={c.id}
                  sx={{
                    display: "flex",
                    gap: 1,
                    alignItems: "center",
                    py: 0.75,
                    borderBottom: "1px solid",
                    borderColor: "divider",
                  }}
                >
                  <Typography variant="body2" sx={{ flex: 1 }}>
                    {c.claim_date} · {c.category} · {c.amount}
                  </Typography>
                  <EssStatusChip status={c.status} />
                </Box>
              ))
            )}
          </Stack>
        </EssPanel>
      </Box>
    </EssSection>
  );
}
