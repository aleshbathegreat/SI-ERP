"use client";

import { useEffect, useState } from "react";
import { Alert, Box, CircularProgress, Typography } from "@mui/material";
import EssSection, { EssPanel, EssStatusChip } from "@/components/ess/EssSection";
import { EssActivity, fetchEssActivity } from "@/lib/essApi";
import { getApiErrorMessage } from "@/lib/apiError";

export default function EssActivityPage() {
  const [rows, setRows] = useState<EssActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        setRows(await fetchEssActivity());
      } catch (e: unknown) {
        setErr(getApiErrorMessage(e, "Could not load your activity"));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) {
    return (
      <Box sx={{ display: "grid", placeItems: "center", minHeight: 240 }}>
        <CircularProgress size={32} />
      </Box>
    );
  }

  return (
    <EssSection title="Activity" subtitle="Actions recorded on your account.">
      {err ? <Alert severity="error" sx={{ mb: 2 }}>{err}</Alert> : null}
      <EssPanel>
        {rows.length === 0 ? (
          <Typography color="text.secondary">No activity recorded yet.</Typography>
        ) : (
          rows.map((row) => (
            <Box
              key={row.id}
              sx={{
                display: "flex",
                justifyContent: "space-between",
                gap: 2,
                py: 1.25,
                borderBottom: "1px solid",
                borderColor: "divider",
              }}
            >
              <Box>
                <Typography variant="body2" fontWeight={600}>{row.event}</Typography>
                <Typography variant="caption" color="text.secondary">
                  {row.area} · {new Date(row.created_at).toLocaleString()}
                </Typography>
              </Box>
              <EssStatusChip status={row.outcome || "Completed"} />
            </Box>
          ))
        )}
      </EssPanel>
    </EssSection>
  );
}
