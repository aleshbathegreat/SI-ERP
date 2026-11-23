"use client";

import { Box, Typography } from "@mui/material";

export default function EssSection({
  title,
  subtitle,
  action,
  children,
}: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <Box>
      <Box
        sx={{
          display: "flex",
          alignItems: { xs: "flex-start", sm: "flex-end" },
          justifyContent: "space-between",
          gap: 2,
          mb: 2.5,
          flexWrap: "wrap",
        }}
      >
        <Box>
          <Typography
            component="h1"
            sx={{
              fontFamily: '"Fraunces", Georgia, serif',
              fontWeight: 700,
              fontSize: { xs: "1.65rem", md: "1.9rem" },
              letterSpacing: "-0.03em",
              lineHeight: 1.15,
            }}
          >
            {title}
          </Typography>
          {subtitle ? (
            <Typography color="text.secondary" sx={{ mt: 0.75, maxWidth: 520 }}>
              {subtitle}
            </Typography>
          ) : null}
        </Box>
        {action}
      </Box>
      {children}
    </Box>
  );
}

export function EssPanel({ children }: { children: React.ReactNode }) {
  return (
    <Box
      sx={{
        p: { xs: 2, md: 2.5 },
        borderRadius: 2,
        border: "1px solid",
        borderColor: "divider",
        bgcolor: (t) =>
          t.palette.mode === "dark" ? "rgba(255,255,255,0.03)" : "rgba(255,255,255,0.72)",
        backdropFilter: "blur(8px)",
      }}
    >
      {children}
    </Box>
  );
}

export function EssStatusChip({ status }: { status: string }) {
  const s = (status || "").toLowerCase();
  const tone =
    s === "approved" || s === "present" || s === "paid"
      ? "#0F7A4A"
      : s === "pending" || s === "late"
        ? "#B86E00"
        : s === "rejected" || s === "absent" || s === "exception"
          ? "#B42318"
          : "#5A6A75";
  return (
    <Box
      component="span"
      sx={{
        display: "inline-block",
        px: 1,
        py: 0.25,
        borderRadius: 1,
        fontSize: "0.75rem",
        fontWeight: 600,
        letterSpacing: "0.02em",
        color: tone,
        bgcolor: `${tone}18`,
        textTransform: "capitalize",
      }}
    >
      {status || "—"}
    </Box>
  );
}
