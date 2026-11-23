"use client";

import { ReactNode } from "react";
import Link from "next/link";
import {
  Box,
  Button,
  CircularProgress,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import SaveIcon from "@mui/icons-material/Save";

type Props = {
  title: string;
  subtitle?: string;
  backHref: string;
  backLabel?: string;
  mode: "create" | "edit" | "view";
  loading?: boolean;
  saving?: boolean;
  onSubmit?: () => void;
  onCancel?: () => void;
  extraActions?: ReactNode;
  children: ReactNode;
  maxWidth?: number | string;
  submitLabel?: string;
};

export default function FormPageShell({
  title,
  subtitle,
  backHref,
  backLabel = "Back to list",
  mode,
  loading,
  saving,
  onSubmit,
  onCancel,
  extraActions,
  children,
  maxWidth = 880,
  submitLabel,
}: Props) {
  const readOnly = mode === "view";

  return (
    <Box sx={{ maxWidth, mx: "auto", pb: 10 }}>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        justifyContent="space-between"
        alignItems={{ xs: "stretch", sm: "flex-start" }}
        spacing={1.5}
        sx={{ mb: 2 }}
      >
        <Box>
          <Button
            component={Link}
            href={backHref}
            startIcon={<ArrowBackIcon />}
            size="small"
            sx={{ mb: 1, px: 0 }}
          >
            {backLabel}
          </Button>
          <Typography
            variant="h4"
            sx={{ fontWeight: 650, letterSpacing: "-0.02em", lineHeight: 1.25 }}
          >
            {title}
          </Typography>
          {subtitle ? (
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ mt: 0.5, maxWidth: 520, lineHeight: 1.45 }}
            >
              {subtitle}
            </Typography>
          ) : null}
        </Box>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          {extraActions}
          {!readOnly ? (
            <>
              <Button
                component={Link}
                href={backHref}
                disabled={saving}
                onClick={onCancel}
              >
                Cancel
              </Button>
              <Button
                variant="contained"
                startIcon={<SaveIcon />}
                disabled={saving || loading}
                onClick={onSubmit}
              >
                {saving ? "Saving…" : submitLabel || (mode === "create" ? "Create" : "Save changes")}
              </Button>
            </>
          ) : (
            <Button component={Link} href={backHref} variant="outlined">
              Close
            </Button>
          )}
        </Stack>
      </Stack>

      <Paper
        variant="outlined"
        sx={{
          p: { xs: 2, md: 3 },
          borderRadius: 2,
          bgcolor: "background.paper",
        }}
      >
        {loading ? (
          <Stack alignItems="center" justifyContent="center" py={6}>
            <CircularProgress />
          </Stack>
        ) : (
          <Stack spacing={2.5}>{children}</Stack>
        )}
      </Paper>

      {/* Sticky mobile action bar */}
      {!readOnly ? (
        <Paper
          elevation={8}
          sx={{
            position: "fixed",
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: 20,
            display: { xs: "block", md: "none" },
            borderTop: "1px solid",
            borderColor: "divider",
            px: 2,
            py: 1.5,
          }}
        >
          <Stack direction="row" spacing={1} justifyContent="flex-end">
            <Button component={Link} href={backHref} disabled={saving}>
              Cancel
            </Button>
            <Button
              variant="contained"
              disabled={saving || loading}
              onClick={onSubmit}
            >
              {saving ? "Saving…" : submitLabel || "Save"}
            </Button>
          </Stack>
        </Paper>
      ) : null}
    </Box>
  );
}
