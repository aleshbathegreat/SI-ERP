"use client";

import { ReactNode } from "react";
import { Box, Stack, Typography } from "@mui/material";

export default function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  /** @deprecated Ignored — kept for call-site compatibility */
  moduleKey?: string;
  actions?: ReactNode;
}) {
  return (
    <Stack
      direction={{ xs: "column", sm: "row" }}
      justifyContent="space-between"
      alignItems={{ xs: "stretch", sm: "flex-start" }}
      spacing={1.5}
      sx={{ mb: 3 }}
    >
      <Box sx={{ minWidth: 0 }}>
        <Typography
          variant="h4"
          sx={{
            fontWeight: 650,
            letterSpacing: "-0.02em",
            lineHeight: 1.25,
          }}
        >
          {title}
        </Typography>
        {subtitle ? (
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ mt: 0.5, maxWidth: 560, lineHeight: 1.45 }}
          >
            {subtitle}
          </Typography>
        ) : null}
      </Box>
      {actions ? (
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          {actions}
        </Stack>
      ) : null}
    </Stack>
  );
}
