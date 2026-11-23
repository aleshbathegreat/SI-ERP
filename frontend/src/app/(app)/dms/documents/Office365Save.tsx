"use client";

import { useState } from "react";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  List,
  ListItemButton,
  ListItemText,
  Typography,
} from "@mui/material";
import CloudQueueIcon from "@mui/icons-material/CloudQueue";
import { useSnackbar } from "notistack";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { useRecordAction } from "@/hooks/useRecordAction";

type OfficeFile = { id: string; name: string; size: number; web_url?: string };

function bytes(n: number) {
  if (!n) return "0 B";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function Office365ImportButton({ onDone }: { onDone: () => void }) {
  const { enqueueSnackbar } = useSnackbar();
  const [open, setOpen] = useState(false);
  const [files, setFiles] = useState<OfficeFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState("");

  const openDialog = async () => {
    setLoading(true);
    setOpen(true);
    try {
      const { data } = await api.get<OfficeFile[]>("/dms/documents/office365-files/");
      setFiles(Array.isArray(data) ? data : []);
    } catch (e) {
      setFiles([]);
      enqueueSnackbar(getApiErrorMessage(e, "Microsoft 365 is not connected"), errorSnackbarOpts);
    } finally {
      setLoading(false);
    }
  };

  const save = async (itemId: string) => {
    setSaving(itemId);
    try {
      await api.post("/dms/documents/from-office365/", { item_id: itemId });
      enqueueSnackbar("Saved into Documents", { variant: "success" });
      setOpen(false);
      onDone();
    } catch (e) {
      enqueueSnackbar(getApiErrorMessage(e, "Could not save the file"), errorSnackbarOpts);
    } finally {
      setSaving("");
    }
  };

  return (
    <>
      <Button variant="outlined" startIcon={<CloudQueueIcon />} onClick={() => void openDialog()}>
        Save from Microsoft 365
      </Button>
      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Microsoft 365 files</DialogTitle>
        <DialogContent>
          {loading ? <Typography variant="body2">Loading…</Typography> : null}
          {!loading && !files.length ? (
            <Typography variant="body2">
              No files in the configured OneDrive folder. Connect Microsoft 365 under Settings →
              Integrations.
            </Typography>
          ) : null}
          <List dense>
            {files.map((file) => (
              <ListItemButton
                key={file.id}
                disabled={saving === file.id}
                onClick={() => void save(file.id)}
              >
                <ListItemText
                  primary={file.name}
                  secondary={saving === file.id ? "Saving…" : bytes(file.size)}
                />
              </ListItemButton>
            ))}
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

export function Office365SaveButton({ id, onDone }: { id: string; onDone: () => void }) {
  const { run, busy } = useRecordAction();
  return (
    <Button
      variant="outlined"
      startIcon={<CloudQueueIcon />}
      disabled={busy}
      onClick={() =>
        void run(`m365-${id}`, `/dms/documents/${id}/save-to-office365/`, {
          success: "Saved to Microsoft 365",
        }).then((res) => {
          if (res) onDone();
        })
      }
    >
      Save to Microsoft 365
    </Button>
  );
}
