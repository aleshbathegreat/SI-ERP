"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Button, Chip, Stack, Typography } from "@mui/material";
import FormPageShell from "@/components/crud/FormPageShell";
import ModuleGate from "@/components/ModuleGate";
import api from "@/lib/api";
import { formatDateTime } from "@/lib/format";

const moduleKey = "settings.audit";
const basePath = "/settings/audit";

type EventRow = {
  who?: string;
  role?: string;
  event?: string;
  area?: string;
  outcome?: string;
  change?: string;
  record?: string;
  href?: string;
  created_at?: string;
};

export default function AuditViewPage() {
  const params = useParams();
  const id = String(params.id);
  const [row, setRow] = useState<EventRow | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let live = true;
    api
      .get<EventRow>(`/settings/audit/${id}/`)
      .then((r) => {
        if (live) setRow(r.data);
      })
      .catch(() => {
        if (live) setRow(null);
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    return () => {
      live = false;
    };
  }, [id]);

  const denied = row?.outcome === "Denied";

  return (
    <ModuleGate module={moduleKey}>
      <FormPageShell
        title={row?.event || "Audit event"}
        subtitle={row?.area || "Business activity"}
        backHref={basePath}
        mode="view"
        loading={loading}
      >
        <Stack direction="row" spacing={1} alignItems="center">
          <Chip
            size="small"
            label={row?.outcome || "Completed"}
            color={denied ? "warning" : "success"}
            variant="outlined"
          />
          <Typography variant="body2" color="text.secondary">
            {formatDateTime(row?.created_at)}
          </Typography>
        </Stack>
        <Typography variant="body1">
          By {row?.who || "System"}
          {row?.role ? ` · ${row.role}` : ""}
        </Typography>
        {row?.href ? (
          <Button component={Link} href={row.href} variant="outlined" size="small" sx={{ alignSelf: "flex-start" }}>
            Open {row.record || "the record"}
          </Button>
        ) : null}
        {row?.record ? (
          <Typography variant="body2" color="text.secondary">
            Record: {row.record}
          </Typography>
        ) : null}
        {row?.change ? <Typography variant="body1">{row.change}</Typography> : null}
      </FormPageShell>
    </ModuleGate>
  );
}
