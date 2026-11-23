"use client";

import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Typography,
} from "@mui/material";
import DownloadOutlinedIcon from "@mui/icons-material/DownloadOutlined";
import EssSection, { EssPanel } from "@/components/ess/EssSection";
import { EssDocument, fetchEssDocuments } from "@/lib/essApi";
import { getApiErrorMessage } from "@/lib/apiError";

function mediaUrl(file?: string | null) {
  if (!file) return null;
  if (file.startsWith("http")) return file;
  const api = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";
  const origin = api.replace(/\/api\/?$/, "");
  return `${origin}${file.startsWith("/") ? "" : "/"}${file}`;
}

export default function EssDocumentsPage() {
  const [rows, setRows] = useState<EssDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        setRows(await fetchEssDocuments());
      } catch (e: unknown) {
        setErr(getApiErrorMessage(e, "Could not load documents"));
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
    <EssSection
      title="Documents"
      subtitle="Employment letters, contracts, and certificates issued to you."
    >
      {err ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {err}
        </Alert>
      ) : null}

      <EssPanel>
        {rows.length === 0 ? (
          <Typography color="text.secondary">No documents on file yet.</Typography>
        ) : (
          rows.map((d) => {
            const href = mediaUrl(d.file);
            return (
              <Box
                key={d.id}
                sx={{
                  display: "flex",
                  alignItems: { xs: "flex-start", sm: "center" },
                  justifyContent: "space-between",
                  gap: 2,
                  flexWrap: "wrap",
                  py: 1.5,
                  borderBottom: "1px solid",
                  borderColor: "divider",
                }}
              >
                <Box>
                  <Typography fontWeight={700}>{d.title}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {d.doc_type}
                    {d.reference ? ` · ${d.reference}` : ""}
                    {d.issued_on ? ` · Issued ${d.issued_on}` : ""}
                    {d.expires_on ? ` · Expires ${d.expires_on}` : ""}
                  </Typography>
                </Box>
                {href ? (
                  <Button
                    component="a"
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    variant="outlined"
                    startIcon={<DownloadOutlinedIcon />}
                  >
                    Download
                  </Button>
                ) : (
                  <Typography variant="caption" color="text.secondary">
                    No file attached
                  </Typography>
                )}
              </Box>
            );
          })
        )}
      </EssPanel>
    </EssSection>
  );
}
