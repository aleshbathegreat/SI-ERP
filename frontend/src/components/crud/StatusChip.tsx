"use client";

import { Chip, type ChipProps } from "@mui/material";

export type StatusTone = "default" | "info" | "warning" | "success" | "error" | "primary";

const TONE_MAP: Record<string, StatusTone> = {
  draft: "default",
  pending: "warning",
  submitted: "info",
  approved: "success",
  active: "success",
  confirmed: "info",
  delivered: "info",
  invoiced: "success",
  paid: "success",
  closed: "default",
  matched: "success",
  open: "warning",
  rejected: "error",
  cancelled: "default",
  canceled: "default",
  written_off: "error",
  disposed: "default",
  in_repair: "warning",
  idle: "default",
  received: "success",
};

export function statusTone(status?: string | null): StatusTone {
  if (!status) return "default";
  return TONE_MAP[String(status).toLowerCase()] || "default";
}

export function formatStatusLabel(status?: string | null): string {
  if (!status) return "—";
  return String(status).replace(/_/g, " ");
}

export default function StatusChip({
  status,
  label,
  size = "small",
  ...rest
}: {
  status?: string | null;
  label?: string;
  size?: ChipProps["size"];
} & Omit<ChipProps, "label" | "color" | "size">) {
  const tone = statusTone(status);
  return (
    <Chip
      size={size}
      color={tone}
      label={label || formatStatusLabel(status)}
      sx={{ textTransform: "capitalize", fontWeight: 600 }}
      {...rest}
    />
  );
}
