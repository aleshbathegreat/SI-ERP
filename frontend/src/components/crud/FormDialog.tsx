"use client";

import { ReactNode } from "react";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
} from "@mui/material";

type Props = {
  open: boolean;
  title: string;
  children: ReactNode;
  loading?: boolean;
  submitLabel?: string;
  maxWidth?: "xs" | "sm" | "md" | "lg" | "xl" | false;
  onClose: () => void;
  onSubmit: () => void;
};

export default function FormDialog({
  open,
  title,
  children,
  loading = false,
  submitLabel = "Save",
  maxWidth = "sm",
  onClose,
  onSubmit,
}: Props) {
  return (
    <Dialog open={open} onClose={loading ? undefined : onClose} maxWidth={maxWidth} fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          {children}
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} disabled={loading}>
          Cancel
        </Button>
        <Button variant="contained" onClick={onSubmit} disabled={loading}>
          {loading ? "Saving…" : submitLabel}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
