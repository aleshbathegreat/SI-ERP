"use client";

import { FormEvent, Suspense, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Alert, Box, Button, Card, CardContent, Stack, TextField, Typography } from "@mui/material";
import api from "@/lib/api";

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<Box sx={{ minHeight: "100vh" }} />}>
      <ResetPasswordForm />
    </Suspense>
  );
}

function ResetPasswordForm() {
  const params = useSearchParams();
  const uid = params.get("uid") || "";
  const token = params.get("token") || "";
  const ready = useMemo(() => Boolean(uid && token), [uid, token]);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [detail, setDetail] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setDetail("");
    if (password !== confirm) {
      setError("The two passwords do not match.");
      return;
    }
    setSaving(true);
    try {
      const { data } = await api.post("/auth/password-reset/confirm/", { uid, token, password });
      setDetail(data.detail || "Password updated. You can sign in.");
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "This reset link is not valid.";
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Box sx={{ minHeight: "100vh", display: "grid", placeItems: "center", p: 2 }}>
      <Card sx={{ width: "100%", maxWidth: 420 }}>
        <CardContent sx={{ p: 4 }}>
          <Stack spacing={2} component="form" onSubmit={onSubmit}>
            <Typography variant="h5">Choose a new password</Typography>
            {!ready ? <Alert severity="warning">This reset link is incomplete.</Alert> : null}
            {detail ? <Alert severity="success">{detail}</Alert> : null}
            {error ? <Alert severity="error">{error}</Alert> : null}
            <TextField
              label="New password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              fullWidth
              helperText="At least 10 characters."
            />
            <TextField
              label="Confirm password"
              type="password"
              required
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              autoComplete="new-password"
              fullWidth
            />
            <Button type="submit" variant="contained" disabled={saving || !ready || !!detail}>
              {saving ? "Saving…" : "Update password"}
            </Button>
            <Typography variant="body2">
              <Link href="/login">Sign in</Link>
            </Typography>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
