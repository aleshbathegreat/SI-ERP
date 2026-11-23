"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Box,
  Button,
  IconButton,
  Stack,
  Typography,
  useMediaQuery,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import MenuBookOutlinedIcon from "@mui/icons-material/MenuBookOutlined";
import CloseIcon from "@mui/icons-material/Close";
import MenuIcon from "@mui/icons-material/Menu";
import PrintOutlinedIcon from "@mui/icons-material/PrintOutlined";
import { useState } from "react";
import BrandMark from "@/components/BrandMark";
import ThemeToggle from "@/components/ThemeToggle";

export default function GuideShell({
  sidebar,
  children,
  onPrint,
}: {
  sidebar: React.ReactNode;
  children: React.ReactNode;
  onPrint?: () => void;
}) {
  const theme = useTheme();
  const isDark = theme.palette.mode === "dark";
  const narrow = useMediaQuery(theme.breakpoints.down("md"));
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const router = useRouter();
  const accent = theme.palette.primary.main;
  const surface = isDark ? "rgba(12,18,24,0.94)" : "rgba(255,255,255,0.92)";

  return (
    <Box
      className="sierp-guide-shell"
      sx={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        background: isDark
          ? `radial-gradient(900px 480px at 100% -10%, ${accent}28, transparent 55%), linear-gradient(165deg, #0A1218 0%, #121A22 50%, #0F1419 100%)`
          : `radial-gradient(900px 480px at 0% -10%, ${accent}18, transparent 50%), linear-gradient(165deg, #E8F1F6 0%, #F7FAFC 45%, #EEF3F7 100%)`,
      }}
    >
      <Box
        component="header"
        className="noprint"
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 1,
          px: { xs: 1.5, md: 2.5 },
          py: 1.25,
          borderBottom: "1px solid",
          borderColor: "divider",
          bgcolor: surface,
          backdropFilter: "blur(14px)",
          position: "sticky",
          top: 0,
          zIndex: 30,
        }}
      >
        <Stack direction="row" alignItems="center" spacing={1.25} sx={{ minWidth: 0 }}>
          {narrow ? (
            <IconButton onClick={() => setOpen((v) => !v)} aria-label="Contents">
              {open ? <CloseIcon /> : <MenuIcon />}
            </IconButton>
          ) : null}
          <BrandMark size="sm" showTagline={false} />
          <Box sx={{ minWidth: 0, display: { xs: "none", sm: "block" } }}>
            <Stack direction="row" alignItems="center" spacing={0.75}>
              <MenuBookOutlinedIcon sx={{ color: "primary.main", fontSize: 18 }} />
              <Typography
                sx={{
                  fontFamily: '"Fraunces", Georgia, serif',
                  fontWeight: 700,
                  fontSize: "1.05rem",
                  letterSpacing: "-0.02em",
                }}
              >
                User guide
              </Typography>
            </Stack>
            <Typography variant="caption" color="text.secondary">
              SI-ERP · Finance · HR · Payroll · ESS · Integrations
            </Typography>
          </Box>
        </Stack>
        <Stack direction="row" alignItems="center" spacing={0.75}>
          <Button
            size="small"
            startIcon={<ArrowBackIcon />}
            onClick={() => router.push(pathname.startsWith("/ess") ? "/ess" : "/dashboard")}
            sx={{ textTransform: "none", display: { xs: "none", sm: "inline-flex" } }}
          >
            Back to app
          </Button>
          <Button
            component={Link}
            href="/ess"
            target="_blank"
            rel="noopener noreferrer"
            size="small"
            sx={{ textTransform: "none", display: { xs: "none", md: "inline-flex" } }}
          >
            ESS portal
          </Button>
          {onPrint ? (
            <IconButton onClick={onPrint} aria-label="Print" size="small">
              <PrintOutlinedIcon fontSize="small" />
            </IconButton>
          ) : null}
          <ThemeToggle />
        </Stack>
      </Box>

      <Box sx={{ display: "flex", flex: 1, minHeight: 0, position: "relative" }}>
        {!narrow ? (
          <Box
            component="aside"
            className="noprint"
            sx={{
              width: 280,
              flexShrink: 0,
              borderRight: "1px solid",
              borderColor: "divider",
              bgcolor: surface,
              backdropFilter: "blur(12px)",
              overflow: "auto",
              maxHeight: "calc(100vh - 64px)",
              position: "sticky",
              top: 64,
            }}
          >
            {sidebar}
          </Box>
        ) : null}

        {narrow && open ? (
          <Box
            className="noprint"
            sx={{ position: "absolute", inset: 0, zIndex: 25, display: "flex" }}
          >
            <Box
              sx={{
                width: 280,
                height: "100%",
                bgcolor: surface,
                borderRight: "1px solid",
                borderColor: "divider",
                overflow: "auto",
              }}
            >
              {sidebar}
            </Box>
            <Box sx={{ flex: 1, bgcolor: "rgba(0,0,0,0.35)" }} onClick={() => setOpen(false)} />
          </Box>
        ) : null}

        <Box
          component="main"
          sx={{
            flex: 1,
            p: { xs: 2, md: 3.5 },
            maxWidth: 920,
            width: "100%",
            mx: "auto",
          }}
          onClick={() => narrow && open && setOpen(false)}
        >
          {children}
        </Box>
      </Box>

      <link
        href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&display=swap"
        rel="stylesheet"
      />
    </Box>
  );
}
