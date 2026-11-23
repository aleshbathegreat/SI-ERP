"use client";

import { useEffect, useState } from "react";
import { Alert, Button, Stack, TextField, Typography } from "@mui/material";
import PageHeader from "@/components/PageHeader";
import api from "@/lib/api";
import { useSnackbar } from "notistack";

export default function SecurityPage() {
  const { enqueueSnackbar } = useSnackbar();
  const [secret, setSecret] = useState("");
  const [uri, setUri] = useState("");
  const [enabled, setEnabled] = useState(false);
  const [code, setCode] = useState("");

  const load = async () => {
    const { data } = await api.get("/auth/mfa/setup/");
    setSecret(data.secret || "");
    setUri(data.otpauth_url || "");
    setEnabled(!!data.mfa_enabled);
  };

  useEffect(() => {
    load().catch(() => undefined);
  }, []);

  return (
    <Stack spacing={2}>
      <PageHeader
        title="Security · MFA"
        subtitle="TOTP multi-factor authentication for production access"
      />
      <Alert severity={enabled ? "success" : "warning"}>
        MFA is {enabled ? "enabled" : "not enabled"} for your account.
      </Alert>
      <Typography variant="body2" color="text.secondary">
        Secret: <code>{secret}</code>
      </Typography>
      <Typography variant="body2" sx={{ wordBreak: "break-all" }}>
        otpauth: {uri}
      </Typography>
      <TextField
        label="Authenticator code"
        value={code}
        onChange={(e) => setCode(e.target.value)}
        sx={{ maxWidth: 240 }}
      />
      <Stack direction="row" spacing={1}>
        <Button
          variant="contained"
          onClick={async () => {
            try {
              await api.post("/auth/mfa/setup/", { code });
              enqueueSnackbar("MFA enabled", { variant: "success" });
              load();
            } catch {
              enqueueSnackbar("Invalid code", { variant: "error" });
            }
          }}
        >
          Enable MFA
        </Button>
        <Button
          variant="outlined"
          color="error"
          onClick={async () => {
            try {
              await api.post("/auth/mfa/disable/", { code });
              enqueueSnackbar("MFA disabled", { variant: "success" });
              load();
            } catch {
              enqueueSnackbar("Invalid code", { variant: "error" });
            }
          }}
        >
          Disable MFA
        </Button>
      </Stack>
    </Stack>
  );
}
