"use client";

import { useEffect, useState } from "react";
import {
  Alert,
  Card,
  CardContent,
  Chip,
  Stack,
  Typography,
} from "@mui/material";
import PageHeader from "@/components/PageHeader";
import PlatformGate from "@/components/PlatformGate";
import api from "@/lib/api";

type DomainCfg = {
  platform_root: string | null;
  platform_hosts: string[];
  notes: string;
};

export default function PlatformDomainsPage() {
  const [data, setData] = useState<DomainCfg | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get<DomainCfg>("/platform/domains/")
      .then((r) => setData(r.data))
      .catch(() => setError("Unable to load domain config"));
  }, []);

  return (
    <PlatformGate capability="domains">
      <PageHeader
        title="Platform domains"
        subtitle="Root domain and accepted hosts for tenant subdomains"
      />
      {error ? <Alert severity="error">{error}</Alert> : null}
      <Card variant="outlined">
        <CardContent>
          <Stack spacing={2}>
            <div>
              <Typography variant="caption" color="text.secondary">
                Platform root
              </Typography>
              <Typography variant="h6">
                {data?.platform_root || "— (not set)"}
              </Typography>
            </div>
            <div>
              <Typography variant="caption" color="text.secondary" display="block" mb={1}>
                Accepted hosts
              </Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {(data?.platform_hosts || []).map((h) => (
                  <Chip key={h} label={h} size="small" />
                ))}
                {!data?.platform_hosts?.length ? (
                  <Typography color="text.secondary">None configured</Typography>
                ) : null}
              </Stack>
            </div>
            {data?.notes ? (
              <Alert severity="info">{data.notes}</Alert>
            ) : null}
            <Typography variant="body2" color="text.secondary">
              Custom domains are managed per tenant under Tenants. Env vars:
              PLATFORM_ROOT_DOMAIN, PLATFORM_HOSTS.
            </Typography>
          </Stack>
        </CardContent>
      </Card>
    </PlatformGate>
  );
}
