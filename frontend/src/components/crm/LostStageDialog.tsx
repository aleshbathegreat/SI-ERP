"use client";

import { useEffect, useState } from "react";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
} from "@mui/material";

type Props = {
  open: boolean;
  loading?: boolean;
  title?: string;
  onClose: () => void;
  onConfirm: (reason: string) => void;
};

export default function LostStageDialog({
  open,
  loading = false,
  title = "Mark as lost",
  onClose,
  onConfirm,
}: Props) {
  const [reason, setReason] = useState("");

  useEffect(() => {
    if (open) setReason("");
  }, [open]);

  return (
    <Dialog open={open} onClose={loading ? undefined : onClose} fullWidth maxWidth="xs">
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <TextField
          autoFocus
          fullWidth
          required
          label="Lost reason"
          placeholder="Price, timing, competitor, no budget"
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          sx={{ mt: 1 }}
        />
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} disabled={loading}>
          Cancel
        </Button>
        <Button
          variant="contained"
          color="error"
          disabled={loading || !reason.trim()}
          onClick={() => onConfirm(reason.trim())}
        >
          {loading ? "Saving…" : "Mark lost"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
