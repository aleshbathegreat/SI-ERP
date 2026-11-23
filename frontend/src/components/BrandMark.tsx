"use client";

import { Box, Stack, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useBranding } from "@/components/BrandingProvider";
import { logoForMode } from "@/lib/branding";

type Props = {
  size?: "sm" | "md" | "lg";
  showName?: boolean;
  showTagline?: boolean;
  dense?: boolean;
};

const SIZES = { sm: 32, md: 44, lg: 56 };

export default function BrandMark({
  size = "md",
  showName = true,
  showTagline = false,
  dense = false,
}: Props) {
  const theme = useTheme();
  const { branding } = useBranding();
  const px = SIZES[size];
  const dark = theme.palette.mode === "dark";
  const logo = logoForMode(branding, dark);
  const name = branding.brand_name || "SI-ERP";
  const tagline = branding.brand_tagline || "";
  const accent = branding.brand_primary_color || theme.palette.primary.main;

  return (
    <Stack
      direction="row"
      spacing={dense ? 1 : 1.5}
      alignItems="center"
      sx={{ minWidth: 0 }}
    >
      {logo ? (
        <Box
          component="img"
          src={logo}
          alt={name}
          sx={{
            height: px,
            width: "auto",
            maxWidth: px * 2.4,
            objectFit: "contain",
            display: "block",
          }}
        />
      ) : (
        <Box
          sx={{
            width: px,
            height: px,
            borderRadius: 1.5,
            bgcolor: accent,
            color: "#fff",
            display: "grid",
            placeItems: "center",
            fontWeight: 800,
            fontSize: px * 0.38,
            letterSpacing: 0.5,
            flexShrink: 0,
          }}
        >
          {(name || "S")
            .split(/\s+/)
            .slice(0, 2)
            .map((w) => w[0])
            .join("")
            .toUpperCase()}
        </Box>
      )}
      {showName ? (
        <Box sx={{ minWidth: 0 }}>
          <Typography
            variant={size === "lg" ? "h5" : "h6"}
            color="primary"
            noWrap
            sx={{ lineHeight: 1.2, fontWeight: 700 }}
          >
            {name}
          </Typography>
          {showTagline && tagline ? (
            <Typography variant="caption" color="text.secondary" noWrap display="block">
              {tagline}
            </Typography>
          ) : null}
        </Box>
      ) : null}
    </Stack>
  );
}
