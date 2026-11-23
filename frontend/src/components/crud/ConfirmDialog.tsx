"use client";

import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from "@mui/material";

type Props = {
  open: boolean;
  title?: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  loading?: boolean;
  danger?: boolean;
  onClose: () => void;
  onConfirm: () => void;
};

export default function ConfirmDialog({
  open,
  title = "Confirm action",
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  loading = false,
  danger = true,
  onClose,
  onConfirm,
}: Props) {
  return (
    <Dialog
      open={open}
      onClose={loading ? undefined : onClose}
      maxWidth="xs"
      fullWidth
      aria-labelledby="confirm-dialog-title"
    >
      <DialogTitle id="confirm-dialog-title">{title}</DialogTitle>
      <DialogContent>
        <DialogContentText component="div" sx={{ whiteSpace: "pre-wrap" }}>
          {message}
        </DialogContentText>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} disabled={loading} autoFocus={!danger}>
          {cancelLabel}
        </Button>
        <Button
          variant="contained"
          color={danger ? "error" : "primary"}
          onClick={onConfirm}
          disabled={loading}
          autoFocus={danger}
        >
          {loading ? "Please wait…" : confirmLabel}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
