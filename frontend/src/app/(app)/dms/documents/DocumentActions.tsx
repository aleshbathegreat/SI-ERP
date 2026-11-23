"use client";

import { useRef, useState } from "react";
import {
  Button,
  Link as MuiLink,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import PublishIcon from "@mui/icons-material/Publish";
import ArchiveOutlinedIcon from "@mui/icons-material/ArchiveOutlined";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import { Office365SaveButton } from "./Office365Save";
import { useSnackbar } from "notistack";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { usePermissions } from "@/hooks/usePermissions";
import { useRecordAction } from "@/hooks/useRecordAction";
import { formatDate } from "@/lib/format";

const moduleKey = "dms.documents";

export function DocumentActions({
  id,
  status,
  checkedOut,
  workflow,
  onDone,
}: {
  id: string;
  status: string;
  checkedOut?: boolean;
  workflow?: unknown;
  onDone: () => void;
}) {
  const { enqueueSnackbar } = useSnackbar();
  const { canChange } = usePermissions();
  const { run, busy } = useRecordAction();
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  if (!canChange(moduleKey)) return null;

  const act = async (
    action: "publish" | "archive" | "submit" | "reject" | "restore" | "checkout" | "checkin",
    msg: string
  ) => {
    const res = await run(`${action}-${id}`, `/dms/documents/${id}/${action}/`, {
      success: msg,
    });
    if (res) onDone();
  };

  const upload = async (file: File) => {
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      await api.post(`/dms/documents/${id}/new-version/`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      enqueueSnackbar("File uploaded", { variant: "success" });
      onDone();
    } catch (e) {
      enqueueSnackbar(getApiErrorMessage(e, "Upload failed"), errorSnackbarOpts);
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        hidden
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) void upload(f);
        }}
      />
      <Button
        variant="outlined"
        startIcon={<UploadFileIcon />}
        disabled={busy || uploading}
        onClick={() => inputRef.current?.click()}
      >
        {uploading ? "Uploading…" : "Upload file / new version"}
      </Button>
      <Office365SaveButton id={id} onDone={onDone} />
      {!workflow && status === "draft" ? (
        <Button
          variant="outlined"
          disabled={busy}
          onClick={() => void act("submit", "Sent for review")}
        >
          Submit for review
        </Button>
      ) : null}
      {!workflow && status === "in_review" ? (
        <Button
          variant="outlined"
          disabled={busy}
          onClick={() => void act("reject", "Sent back to draft")}
        >
          Send back
        </Button>
      ) : null}
      {!workflow && status !== "published" && status !== "archived" ? (
        <Button
          variant="contained"
          color="secondary"
          startIcon={<PublishIcon />}
          disabled={busy}
          onClick={() => void act("publish", "Document published")}
        >
          Publish
        </Button>
      ) : null}
      {!workflow && status === "archived" ? (
        <Button
          variant="outlined"
          disabled={busy}
          onClick={() => void act("restore", "Document restored")}
        >
          Restore
        </Button>
      ) : null}
      {!workflow && status !== "archived" ? (
        <Button
          variant="outlined"
          startIcon={<ArchiveOutlinedIcon />}
          disabled={busy}
          onClick={() => void act("archive", "Document archived")}
        >
          Archive
        </Button>
      ) : null}
      {status !== "archived" ? (
        <Button
          variant="outlined"
          disabled={busy}
          onClick={() =>
            void act(
              checkedOut ? "checkin" : "checkout",
              checkedOut ? "Checked in" : "Checked out"
            )
          }
        >
          {checkedOut ? "Check in" : "Check out"}
        </Button>
      ) : null}
    </>
  );
}

type Version = {
  id: number;
  version: number;
  file: string | null;
  notes: string;
  created_at: string;
};

export function DocumentVersions({
  file,
  versions,
}: {
  file: string | null;
  versions: Version[];
}) {
  return (
    <Paper variant="outlined" sx={{ p: 2, mt: 2 }}>
      <Typography variant="subtitle1" sx={{ mb: 1 }}>
        File &amp; versions
      </Typography>
      <Typography variant="body2" sx={{ mb: 1 }}>
        Current file:{" "}
        {file ? (
          <MuiLink href={file} target="_blank" rel="noopener noreferrer">
            Download
          </MuiLink>
        ) : (
          "none uploaded"
        )}
      </Typography>
      {versions.length ? (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Version</TableCell>
              <TableCell>Uploaded</TableCell>
              <TableCell>File</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {versions.map((v) => (
              <TableRow key={v.id}>
                <TableCell>v{v.version}</TableCell>
                <TableCell>{formatDate(v.created_at)}</TableCell>
                <TableCell>
                  {v.file ? (
                    <MuiLink href={v.file} target="_blank" rel="noopener noreferrer">
                      Download
                    </MuiLink>
                  ) : (
                    "—"
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : null}
    </Paper>
  );
}
