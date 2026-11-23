"use client";

import Link from "next/link";
import { Button, IconButton, Tooltip } from "@mui/material";
import HelpOutlineIcon from "@mui/icons-material/HelpOutlineOutlined";

/** Contextual jump into /guide#section — prefer this over a separate docs site. */
export default function GuideLink({
  section,
  label = "Guide",
  iconOnly = false,
  size = "small",
}: {
  section: string;
  label?: string;
  iconOnly?: boolean;
  size?: "small" | "medium";
}) {
  const href = `/guide#${section}`;
  if (iconOnly) {
    return (
      <Tooltip title={`Open guide · ${label}`}>
        <IconButton
          component={Link}
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          size={size}
          aria-label={label}
          color="primary"
        >
          <HelpOutlineIcon fontSize="inherit" />
        </IconButton>
      </Tooltip>
    );
  }
  return (
    <Button
      component={Link}
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      size={size}
      startIcon={<HelpOutlineIcon />}
      sx={{ textTransform: "none" }}
    >
      {label}
    </Button>
  );
}
