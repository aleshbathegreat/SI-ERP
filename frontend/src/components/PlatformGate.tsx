"use client";

import { Box, Button, Typography } from "@mui/material";
import Link from "next/link";
import { usePlatformCaps } from "@/hooks/usePlatformCaps";

/** Platform staff (owner / finance / sales / support / technical) only. */
export default function PlatformGate({
  children,
  capability,
}: {
  children: React.ReactNode;
  capability?: string;
}) {
  const { isPlatformUser, can, platformRole } = usePlatformCaps();

  if (!isPlatformUser) {
    return (
      <Box sx={{ py: 8, textAlign: "center", maxWidth: 520, mx: "auto" }}>
        <Typography variant="h5" gutterBottom>
          Platform access only
        </Typography>
        <Typography color="text.secondary" mb={2}>
          This screen is reserved for SI-ERP platform staff. Tenant users cannot manage SaaS
          operations.
        </Typography>
        <Button component={Link} href="/dashboard" variant="outlined">
          Back to tenant dashboard
        </Button>
      </Box>
    );
  }

  if (capability && !can(capability)) {
    return (
      <Box sx={{ py: 8, textAlign: "center", maxWidth: 520, mx: "auto" }}>
        <Typography variant="h5" gutterBottom>
          Insufficient platform role
        </Typography>
        <Typography color="text.secondary" mb={2}>
          Your role ({platformRole || "none"}) cannot access this area. Required: {capability}.
        </Typography>
        <Button component={Link} href="/platform" variant="outlined">
          Platform home
        </Button>
      </Box>
    );
  }

  return <>{children}</>;
}
