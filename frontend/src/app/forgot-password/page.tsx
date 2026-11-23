"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { Alert, Box, Button, Card, CardContent, Stack, TextField, Typography } from "@mui/material";
import api from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [detail, setDetail] = useState("");
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSending(true);
    setError("");
    setDetail("");
    try {
      const { data } = await api.post("/auth/password-reset/", { email });
      setDetail(data.detail || "If an account exists for that email, a reset link has been sent.");
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Could not send the reset email.";
      setError(message);
    } finally {
      setSending(false);
    }
  };

  return (
    <Box sx={{ minHeight: "100vh", display: "grid", placeItems: "center", p: 2 }}>
      <Card sx={{ width: "100%", maxWidth: 420 }}>
        <CardContent sx={{ p: 4 }}>
          <Stack spacing={2} component="form" onSubmit={onSubmit}>
            <Typography variant="h5">Forgot password</Typography>
            <Typography variant="body2" color="text.secondary">
              Enter the email on the account. If it matches, the platform mailbox sends a reset link.
            </Typography>
            {detail ? <Alert severity="success">{detail}</Alert> : null}
            {error ? <Alert severity="error">{error}</Alert> : null}
            <TextField
              label="Email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              fullWidth
            />
            <Button type="submit" variant="contained" disabled={sending}>
              {sending ? "Sending…" : "Send reset link"}
            </Button>
            <Typography variant="body2">
              <Link href="/login">Back to sign in</Link>
            </Typography>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
