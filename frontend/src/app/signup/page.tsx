"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
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
import BusinessIcon from "@mui/icons-material/Business";
import { useTheme } from "@mui/material/styles";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { signupRequest } from "@/store/auth/slice";
import ThemeToggle from "@/components/ThemeToggle";

export default function SignupPage() {
  const dispatch = useAppDispatch();
  const router = useRouter();
  const theme = useTheme();
  const isDark = theme.palette.mode === "dark";
  const { loading, error, access } = useAppSelector((s) => s.auth);
  const [form, setForm] = useState({
    company_name: "",
    username: "",
    email: "",
    password: "",
    first_name: "",
    last_name: "",
    phone: "",
  });

  useEffect(() => {
    if (access) router.replace("/dashboard");
  }, [access, router]);

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    dispatch(signupRequest(form));
  };

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        background: isDark
          ? "radial-gradient(circle at top right, #1B6A94 0%, transparent 30%), linear-gradient(160deg, #0A1218 0%, #121A22 45%, #0F1419 45%)"
          : "radial-gradient(circle at top right, #1B6A94 0%, transparent 35%), linear-gradient(160deg, #072A40 0%, #0B3D5C 40%, #F4F7FA 40%)",
        p: 2,
        position: "relative",
      }}
    >
      <Box sx={{ position: "absolute", top: 16, right: 16 }}>
        <ThemeToggle />
      </Box>
      <Card sx={{ width: "100%", maxWidth: 520 }}>
        <CardContent sx={{ p: 4 }}>
          <Stack spacing={2}>
            <BusinessIcon color="primary" fontSize="large" />
            <Typography variant="h5">Start your ERP trial</Typography>
            <Typography variant="body2" color="text.secondary">
              14-day SaaS trial with Finance, HR and Payroll — inspired by multi-tenant desk model.
            </Typography>
            {error ? <Alert severity="error">{error}</Alert> : null}
            <Box component="form" onSubmit={onSubmit}>
              <Stack spacing={2}>
                <TextField label="Company name" required value={form.company_name} onChange={set("company_name")} />
                <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
                  <TextField label="First name" value={form.first_name} onChange={set("first_name")} fullWidth />
                  <TextField label="Last name" value={form.last_name} onChange={set("last_name")} fullWidth />
                </Stack>
                <TextField label="Username" required value={form.username} onChange={set("username")} />
                <TextField label="Work email" type="email" required value={form.email} onChange={set("email")} />
                <TextField label="Phone" value={form.phone} onChange={set("phone")} />
                <TextField
                  label="Password"
                  type="password"
                  required
                  value={form.password}
                  onChange={set("password")}
                />
                <Button type="submit" variant="contained" size="large" disabled={loading}>
                  {loading ? "Creating tenant..." : "Create company & start trial"}
                </Button>
                <Typography variant="body2" color="text.secondary">
                  Creating a company means you agree to the <Link href="/legal/terms">terms</Link> and the{" "}
                  <Link href="/legal/privacy">privacy notice</Link>.
                </Typography>
                <Typography variant="body2">
                  Already have an account? <Link href="/login">Sign in</Link> · <Link href="/">Product</Link>
                </Typography>
              </Stack>
            </Box>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
