"use client";

import { ReactNode } from "react";
import Link from "next/link";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Button,
  CircularProgress,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import StatusChip from "@/components/crud/StatusChip";

export type DetailMetric = {
  label: string;
  value: ReactNode;
  hint?: string;
};

type Props = {
  title: string;
  subtitle?: string;
  eyebrow?: string;
  backHref: string;
  backLabel?: string;
  status?: string | null;
  statusLabel?: string;
  meta?: ReactNode;
  metrics?: DetailMetric[];
  loading?: boolean;
  extraActions?: ReactNode;
  children: ReactNode;
  maxWidth?: number | string;
};

export default function DetailPageShell({
  title,
  subtitle,
  eyebrow,
  backHref,
  backLabel = "Back to list",
  status,
  statusLabel,
  meta,
  metrics,
  loading,
  extraActions,
  children,
  maxWidth = 960,
}: Props) {
  return (
    <Box sx={{ maxWidth, mx: "auto", pb: 6 }}>
      <Button
        component={Link}
        href={backHref}
        startIcon={<ArrowBackIcon />}
        size="small"
        sx={{ mb: 1.5, px: 0 }}
      >
        {backLabel}
      </Button>

      <Stack
        direction={{ xs: "column", md: "row" }}
        justifyContent="space-between"
        alignItems={{ xs: "stretch", md: "flex-start" }}
        spacing={2}
        sx={{ mb: 2.5 }}
      >
        <Box sx={{ minWidth: 0 }}>
          {eyebrow ? (
            <Typography
              variant="overline"
              color="text.secondary"
              sx={{ letterSpacing: 1.1, display: "block", lineHeight: 1.2 }}
            >
              {eyebrow}
            </Typography>
          ) : null}
          <Stack direction="row" spacing={1.25} alignItems="center" flexWrap="wrap" useFlexGap>
            <Typography
              variant="h4"
              sx={{ fontWeight: 650, letterSpacing: "-0.02em", wordBreak: "break-word" }}
            >
              {title}
            </Typography>
            {status ? <StatusChip status={status} label={statusLabel} /> : null}
          </Stack>
          {subtitle ? (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75 }}>
              {subtitle}
            </Typography>
          ) : null}
          {meta ? <Box sx={{ mt: 1 }}>{meta}</Box> : null}
        </Box>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          {extraActions}
          <Button component={Link} href={backHref} variant="outlined">
            Close
          </Button>
        </Stack>
      </Stack>

      {metrics && metrics.length > 0 ? (
        <Box
          sx={{
            display: "grid",
            gap: 1.5,
            gridTemplateColumns: {
              xs: "1fr 1fr",
              md: `repeat(${Math.min(metrics.length, 4)}, minmax(0, 1fr))`,
            },
            mb: 2.5,
          }}
        >
          {metrics.map((m) => (
            <Paper
              key={m.label}
              variant="outlined"
              sx={{
                p: 2,
                borderRadius: 2,
                bgcolor: "background.paper",
                minHeight: 92,
              }}
            >
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ textTransform: "uppercase", letterSpacing: 0.6 }}
              >
                {m.label}
              </Typography>
              <Typography variant="h6" sx={{ mt: 0.5, fontWeight: 700, lineHeight: 1.25 }}>
                {m.value}
              </Typography>
              {m.hint ? (
                <Typography variant="caption" color="text.secondary">
                  {m.hint}
                </Typography>
              ) : null}
            </Paper>
          ))}
        </Box>
      ) : null}

      {loading ? (
        <Paper variant="outlined" sx={{ p: 6, borderRadius: 2 }}>
          <Stack alignItems="center">
            <CircularProgress />
          </Stack>
        </Paper>
      ) : (
        <Stack spacing={2}>{children}</Stack>
      )}
    </Box>
  );
}

export function DetailSection({
  title,
  description,
  children,
  action,
  defaultExpanded = true,
  collapsible = true,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  action?: ReactNode;
  /** When false, renders a static paper (no accordion). */
  collapsible?: boolean;
  defaultExpanded?: boolean;
}) {
  if (!collapsible) {
    return (
      <Paper variant="outlined" sx={{ borderRadius: 2, p: { xs: 2, md: 2.5 } }}>
        <Stack
          direction="row"
          justifyContent="space-between"
          alignItems="flex-start"
          sx={{ mb: 1.5 }}
        >
          <Box>
            <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
              {title}
            </Typography>
            {description ? (
              <Typography variant="body2" color="text.secondary">
                {description}
              </Typography>
            ) : null}
          </Box>
          {action}
        </Stack>
        {children}
      </Paper>
    );
  }

  return (
    <Accordion
      defaultExpanded={defaultExpanded}
      disableGutters
      elevation={0}
      sx={{
        border: "1px solid",
        borderColor: "divider",
        borderRadius: "8px !important",
        "&:before": { display: "none" },
        overflow: "hidden",
      }}
    >
      <AccordionSummary
        expandIcon={<ExpandMoreIcon />}
        sx={{
          px: { xs: 2, md: 2.5 },
          minHeight: 56,
          "& .MuiAccordionSummary-content": {
            my: 1.25,
            alignItems: "center",
            justifyContent: "space-between",
            gap: 1,
            pr: 1,
          },
        }}
      >
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
            {title}
          </Typography>
          {description ? (
            <Typography variant="body2" color="text.secondary">
              {description}
            </Typography>
          ) : null}
        </Box>
        {action ? (
          <Box
            onClick={(e) => e.stopPropagation()}
            onFocus={(e) => e.stopPropagation()}
            sx={{ flexShrink: 0 }}
          >
            {action}
          </Box>
        ) : null}
      </AccordionSummary>
      <AccordionDetails sx={{ px: { xs: 2, md: 2.5 }, pt: 0, pb: 2.5 }}>
        {children}
      </AccordionDetails>
    </Accordion>
  );
}

export function DetailGrid({ children }: { children: ReactNode }) {
  return (
    <Box
      sx={{
        display: "grid",
        gap: { xs: 2, md: 2.5 },
        gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
      }}
    >
      {children}
    </Box>
  );
}

export function DetailItem({
  label,
  value,
  fullWidth,
}: {
  label: string;
  value: ReactNode;
  fullWidth?: boolean;
}) {
  return (
    <Box sx={fullWidth ? { gridColumn: { sm: "1 / -1" } } : undefined}>
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ display: "block", mb: 0.35, textTransform: "uppercase", letterSpacing: 0.5 }}
      >
        {label}
      </Typography>
      <Typography variant="body1" sx={{ fontWeight: 500, wordBreak: "break-word" }}>
        {value === null || value === undefined || value === "" ? "—" : value}
      </Typography>
    </Box>
  );
}
