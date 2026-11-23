"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Button, Chip, Paper, Stack, Typography } from "@mui/material";
import api from "@/lib/api";
import { listResource } from "@/lib/crudApi";
import { RECORD_HREF, workflowTargetLabel } from "../dms/workflows/workflowTargets";

type Task = {
  id: number;
  title: string;
  body: string;
  status: string;
  module: string;
  object_id: string;
  role_code: string;
  role_name: string;
  created_at: string;
};

export default function TasksPage() {
  const [rows, setRows] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await listResource<Task>("/work-tasks/"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const complete = async (row: Task) => {
    await api.post(`/work-tasks/${row.id}/complete/`);
    load();
  };

  return (
    <Stack spacing={2}>
      <div>
        <Typography variant="h5" fontWeight={700}>
          Tasks
        </Typography>
        <Typography color="text.secondary" variant="body2">
          Work assigned to you or your role. A workflow can create these.
        </Typography>
      </div>
      {loading ? <Typography color="text.secondary">Loading…</Typography> : null}
      {!loading && rows.length === 0 ? (
        <Typography color="text.secondary">No tasks.</Typography>
      ) : null}
      {rows.map((row) => {
        const href = row.object_id && RECORD_HREF[row.module] ? `${RECORD_HREF[row.module]}/${row.object_id}` : "";
        return (
          <Paper key={row.id} variant="outlined" sx={{ p: 2 }}>
            <Stack direction="row" spacing={1} alignItems="center">
              <Typography fontWeight={700} sx={{ flex: 1 }}>
                {row.title}
              </Typography>
              <Chip size="small" label={row.status} color={row.status === "open" ? "warning" : "success"} />
              {row.status === "open" ? (
                <Button size="small" variant="outlined" onClick={() => complete(row)}>
                  Done
                </Button>
              ) : null}
            </Stack>
            {row.body ? (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                {row.body}
              </Typography>
            ) : null}
            <Stack direction="row" spacing={2} sx={{ mt: 1 }}>
              <Typography variant="caption" color="text.secondary">
                {row.role_name || row.role_code || "Assigned"} · {new Date(row.created_at).toLocaleString()}
              </Typography>
              {href ? (
                <Typography variant="caption" component={Link} href={href}>
                  {workflowTargetLabel(row.module)}
                </Typography>
              ) : null}
            </Stack>
          </Paper>
        );
      })}
    </Stack>
  );
}
