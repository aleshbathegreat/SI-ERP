"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import Link from "next/link";
import { useTheme } from "@mui/material/styles";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { loginRequest } from "@/store/auth/slice";
import ThemeToggle from "@/components/ThemeToggle";
import BrandMark from "@/components/BrandMark";
import { useBranding } from "@/components/BrandingProvider";
import { endSession, sessionExpired } from "@/lib/session";

export default function LoginPage() {
  const dispatch = useAppDispatch();
  const router = useRouter();
  const theme = useTheme();
  const isDark = theme.palette.mode === "dark";
  const { branding } = useBranding();
  const { loading, error, access } = useAppSelector((s) => s.auth);
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("Admin@123");
  const [mfaCode, setMfaCode] = useState("");

  const user = useAppSelector((s) => s.auth.user);
  const organization = useAppSelector((s) => s.auth.organization);
  const isPlatformUser = useAppSelector((s) => s.auth.isPlatformUser);
  const permissions = useAppSelector((s) => s.auth.permissions);

  useEffect(() => {
    if (sessionExpired()) {
      endSession();
      return;
    }
    if (access || localStorage.getItem("access_token")) {
      if ((isPlatformUser || user?.is_superuser) && !organization) {
        router.replace("/platform");
        return;
      }
      const keys = Object.keys(permissions || {});
      const essOnly =
        keys.includes("ess") &&
        !keys.some(
          (k) =>
            k !== "ess" &&
            k !== "dashboard" &&
            k !== "hr.leaves" &&
            k !== "hr.attendance" &&
            k !== "payroll.payslips"
        );
      router.replace(essOnly ? "/ess" : "/dashboard");
    }
  }, [access, router, user?.is_superuser, isPlatformUser, organization, permissions]);

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (loading) return;
    dispatch(loginRequest({ username, password, mfa_code: mfaCode || undefined }));
  };

  const accent = branding.brand_primary_color || "#1B6A94";
  const isTenant = branding.mode === "tenant";

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        background: isDark
          ? `radial-gradient(circle at top left, ${accent} 0%, transparent 35%), linear-gradient(160deg, #0A1218 0%, #121A22 50%, #0F1419 50%)`
          : `radial-gradient(circle at top left, ${accent} 0%, transparent 40%), linear-gradient(160deg, #072A40 0%, #0B3D5C 45%, #F4F7FA 45%)`,
        p: 2,
        position: "relative",
      }}
    >
      <Box sx={{ position: "absolute", top: 16, right: 16 }}>
        <ThemeToggle />
      </Box>
      <Card sx={{ width: "100%", maxWidth: 420 }}>
        <CardContent sx={{ p: 4 }}>
          <Stack spacing={2} alignItems="flex-start">
            <BrandMark size="lg" showTagline />
            <Typography variant="body2" color="text.secondary">
              {isTenant
                ? `Sign in to ${branding.name || branding.brand_name}`
                : "Sign in to Finance, HR & Payroll"}
            </Typography>
            {error ? <Alert severity="error">{error}</Alert> : null}
            <Box component="form" onSubmit={onSubmit} sx={{ width: "100%" }}>
              <Stack spacing={2}>
                <TextField
                  label="Username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  fullWidth
                  required
                  autoComplete="username"
                />
                <TextField
                  label="Password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  fullWidth
                  required
                  autoComplete="current-password"
                />
                <TextField
                  label="MFA code (if enabled)"
                  value={mfaCode}
                  onChange={(e) => setMfaCode(e.target.value)}
                  fullWidth
                  inputProps={{ inputMode: "numeric", autoComplete: "one-time-code" }}
                />
                <Button
                  type="submit"
                  variant="contained"
                  size="large"
                  disabled={loading}
                  sx={{ bgcolor: accent, "&:hover": { bgcolor: accent, filter: "brightness(0.92)" } }}
                >
                  {loading ? "Signing in…" : "Sign in"}
                </Button>
                {!isTenant ? (
                  <Typography variant="body2">
                    New company? <Link href="/signup">Start free trial</Link> ·{" "}
                    <Link href="/forgot-password">Forgot password</Link> ·{" "}
                    <Link href="/pricing">View plans</Link> · <Link href="/">Product</Link>
                  </Typography>
                ) : (
                  <>
                    <Typography variant="body2">
                      <Link href="/forgot-password">Forgot password</Link>
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Tenant workspace
                      {branding.code ? ` · ${branding.code}` : ""}
                    </Typography>
                  </>
                )}
              </Stack>
            </Box>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
