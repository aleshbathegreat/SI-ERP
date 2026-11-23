"use client";

import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import EssSection, { EssPanel, EssStatusChip } from "@/components/ess/EssSection";
import { EssReview, fetchEssPerformance, patchEssPerformance } from "@/lib/essApi";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { useSnackbar } from "notistack";

export default function EssPerformancePage() {
  const { enqueueSnackbar } = useSnackbar();
  const [rows, setRows] = useState<EssReview[]>([]);
  const [drafts, setDrafts] = useState<Record<number, { self_rating: string; achievements: string }>>({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<number | null>(null);
  const [err, setErr] = useState("");

  const apply = (list: EssReview[]) => {
    setRows(list);
    setDrafts(
      Object.fromEntries(
        list.map((row) => [row.id, { self_rating: row.self_rating || "", achievements: row.achievements || "" }]),
      ),
    );
  };

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        apply(await fetchEssPerformance());
      } catch (e: unknown) {
        setErr(getApiErrorMessage(e, "Could not load reviews"));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const save = async (id: number) => {
    const draft = drafts[id];
    if (!draft) return;
    setBusy(id);
    try {
      apply(await patchEssPerformance({ id, self_rating: draft.self_rating, achievements: draft.achievements }));
      enqueueSnackbar("Self review saved", { variant: "success" });
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Could not save the review"), errorSnackbarOpts);
    } finally {
      setBusy(null);
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
    <EssSection title="Performance" subtitle="Your goals and appraisals. Add your own notes until the review is approved.">
      {err ? <Alert severity="error" sx={{ mb: 2 }}>{err}</Alert> : null}
      {rows.length === 0 ? (
        <EssPanel>
          <Typography color="text.secondary">No performance reviews are assigned yet.</Typography>
        </EssPanel>
      ) : (
        <Stack spacing={2}>
          {rows.map((row) => {
            const closed = row.status === "approved";
            const draft = drafts[row.id] || { self_rating: "", achievements: "" };
            return (
              <EssPanel key={row.id}>
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                  <Typography fontWeight={700}>{row.period_label}</Typography>
                  <EssStatusChip status={row.status} />
                </Stack>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                  {[row.review_type, row.reviewer_name ? `Reviewer ${row.reviewer_name}` : "", row.rating ? `Rating ${row.rating}` : ""]
                    .filter(Boolean)
                    .join(" · ")}
                </Typography>
                {row.goals ? (
                  <Typography variant="body2" sx={{ mb: 1.5, whiteSpace: "pre-wrap" }}>{row.goals}</Typography>
                ) : null}
                {row.feedback ? (
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5, whiteSpace: "pre-wrap" }}>
                    {row.feedback}
                  </Typography>
                ) : null}
                <Stack spacing={1.5} sx={{ maxWidth: 560 }}>
                  <TextField
                    label="Your rating"
                    value={draft.self_rating}
                    disabled={closed}
                    onChange={(e) =>
                      setDrafts((prev) => ({ ...prev, [row.id]: { ...draft, self_rating: e.target.value } }))
                    }
                  />
                  <TextField
                    label="Your achievements"
                    value={draft.achievements}
                    disabled={closed}
                    multiline
                    minRows={3}
                    onChange={(e) =>
                      setDrafts((prev) => ({ ...prev, [row.id]: { ...draft, achievements: e.target.value } }))
                    }
                  />
                  {closed ? null : (
                    <Button variant="contained" disabled={busy === row.id} onClick={() => save(row.id)} sx={{ alignSelf: "flex-start" }}>
                      Save self review
                    </Button>
                  )}
                </Stack>
              </EssPanel>
            );
          })}
        </Stack>
      )}
    </EssSection>
  );
}
