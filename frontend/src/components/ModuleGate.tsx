"use client";

import { Box, Button, Typography } from "@mui/material";
import Link from "next/link";
import { usePermissions } from "@/hooks/usePermissions";

export default function ModuleGate({
  module,
  children,
}: {
  module: string;
  children: React.ReactNode;
}) {
  const { canView } = usePermissions();
  if (!canView(module)) {
    return (
      <Box sx={{ py: 8, textAlign: "center" }}>
        <Typography variant="h5" gutterBottom>
          Access denied
        </Typography>
        <Typography color="text.secondary" mb={2}>
          You do not have permission to view this module ({module}).
        </Typography>
        <Button component={Link} href="/dashboard" variant="outlined">
          Back to dashboard
        </Button>
      </Box>
    );
  }
  return <>{children}</>;
}
