"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Button, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";
import api from "@/lib/api";
import { listResource } from "@/lib/crudApi";
import { RECORD_HREF, WORKFLOW_TARGETS, workflowTargetLabel } from "../dms/workflows/workflowTargets";

type Comment = {
  id: number;
  module: string;
  object_id: string;
  body: string;
  author_name: string;
  created_at: string;
};

export default function CommentsPage() {
  const [module, setModule] = useState("finance.journals");
  const [objectId, setObjectId] = useState("");
  const [body, setBody] = useState("");
  const [rows, setRows] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const query = new URLSearchParams(window.location.search);
    if (query.get("module")) setModule(query.get("module") || "");
    if (query.get("object")) setObjectId(query.get("object") || "");
  }, []);

  const load = useCallback(async () => {
    if (!module || !objectId) {
      setRows([]);
      return;
    }
    setLoading(true);
    try {
      setRows(
        await listResource<Comment>("/comments/", {
          module,
          object_id: objectId,
        })
      );
    } finally {
      setLoading(false);
    }
  }, [module, objectId]);

  useEffect(() => {
    load();
  }, [load]);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!body.trim() || !objectId) return;
    await api.post("/comments/", { module, object_id: objectId, body });
    setBody("");
    load();
  };

  const recordHref = objectId && RECORD_HREF[module] ? `${RECORD_HREF[module]}/${objectId}` : "";

  return (
    <Stack spacing={2}>
      <div>
        <Typography variant="h5" fontWeight={700}>
          Comments
        </Typography>
        <Typography color="text.secondary" variant="body2">
          Notes on any SI-ERP record. Workflows can add these automatically.
        </Typography>
      </div>
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack component="form" spacing={2} onSubmit={onSubmit}>
          <TextField
            size="small"
            select
            label="Record type"
            value={module}
            onChange={(e) => setModule(e.target.value)}
          >
            {WORKFLOW_TARGETS.map((row) => (
              <MenuItem key={row.value} value={row.value}>
                {row.label}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            size="small"
            label="Record id"
            value={objectId}
            onChange={(e) => setObjectId(e.target.value)}
            required
          />
          <TextField
            size="small"
            label="Comment"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            multiline
            minRows={2}
            required
          />
          <Stack direction="row" spacing={1}>
            <Button type="submit" variant="contained" disabled={!objectId || !body.trim()}>
              Add comment
            </Button>
            {recordHref ? (
              <Button component={Link} href={recordHref}>
                Open {workflowTargetLabel(module)}
              </Button>
            ) : null}
          </Stack>
        </Stack>
      </Paper>
      {loading ? <Typography color="text.secondary">Loading…</Typography> : null}
      {!loading && objectId && rows.length === 0 ? (
        <Typography color="text.secondary">No comments on this record.</Typography>
      ) : null}
      {rows.map((row) => (
        <Paper key={row.id} variant="outlined" sx={{ p: 2 }}>
          <Typography variant="body2">{row.body}</Typography>
          <Typography variant="caption" color="text.secondary">
            {row.author_name || "Workflow"} · {new Date(row.created_at).toLocaleString()}
          </Typography>
        </Paper>
      ))}
    </Stack>
  );
}
