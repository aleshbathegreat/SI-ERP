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
import HomeOutlinedIcon from "@mui/icons-material/HomeOutlined";
import EventAvailableOutlinedIcon from "@mui/icons-material/EventAvailableOutlined";
import FingerprintOutlinedIcon from "@mui/icons-material/FingerprintOutlined";
import PaymentsOutlinedIcon from "@mui/icons-material/PaymentsOutlined";
import FolderOutlinedIcon from "@mui/icons-material/FolderOutlined";
import ReceiptLongOutlinedIcon from "@mui/icons-material/ReceiptLongOutlined";
import ChatOutlinedIcon from "@mui/icons-material/ChatOutlined";
import InsightsOutlinedIcon from "@mui/icons-material/InsightsOutlined";
import HistoryOutlinedIcon from "@mui/icons-material/HistoryOutlined";
import AssignmentOutlinedIcon from "@mui/icons-material/AssignmentOutlined";
import NotificationsNoneOutlinedIcon from "@mui/icons-material/NotificationsNoneOutlined";
import PersonOutlineIcon from "@mui/icons-material/PersonOutlined";
import MenuIcon from "@mui/icons-material/Menu";
import CloseIcon from "@mui/icons-material/Close";
import LogoutIcon from "@mui/icons-material/Logout";
import { useState } from "react";
import BrandMark from "@/components/BrandMark";
import ThemeToggle from "@/components/ThemeToggle";
import { useAppDispatch } from "@/store/hooks";
import { logout } from "@/store/auth/slice";

const NAV = [
  { href: "/ess", label: "Home", icon: <HomeOutlinedIcon fontSize="small" />, exact: true },
  { href: "/ess/leave", label: "Leave", icon: <EventAvailableOutlinedIcon fontSize="small" /> },
  {
    href: "/ess/attendance",
    label: "Attendance",
    icon: <FingerprintOutlinedIcon fontSize="small" />,
  },
  { href: "/ess/payslips", label: "Payslips", icon: <PaymentsOutlinedIcon fontSize="small" /> },
  { href: "/ess/documents", label: "Documents", icon: <FolderOutlinedIcon fontSize="small" /> },
  { href: "/ess/claims", label: "Claims", icon: <ReceiptLongOutlinedIcon fontSize="small" /> },
  { href: "/ess/chat", label: "Chat", icon: <ChatOutlinedIcon fontSize="small" /> },
  { href: "/ess/tasks", label: "Tasks", icon: <AssignmentOutlinedIcon fontSize="small" /> },
  { href: "/ess/notifications", label: "Notifications", icon: <NotificationsNoneOutlinedIcon fontSize="small" /> },
  { href: "/ess/performance", label: "Performance", icon: <InsightsOutlinedIcon fontSize="small" /> },
  { href: "/ess/activity", label: "Activity", icon: <HistoryOutlinedIcon fontSize="small" /> },
  { href: "/ess/profile", label: "Profile", icon: <PersonOutlineIcon fontSize="small" /> },
];

export default function EssShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const theme = useTheme();
  const isDark = theme.palette.mode === "dark";
  const narrow = useMediaQuery(theme.breakpoints.down("md"));
  const [open, setOpen] = useState(false);
  const dispatch = useAppDispatch();

  const accent = theme.palette.primary.main;
  const railBg = isDark ? "rgba(15,20,25,0.92)" : "rgba(255,255,255,0.88)";

  const isActive = (href: string, exact?: boolean) => {
    if (exact) return pathname === href;
    return pathname === href || pathname.startsWith(`${href}/`);
  };

  const doLogout = () => {
    localStorage.clear();
    dispatch(logout());
    router.replace("/login");
  };

  const rail = (
    <Box
      component="nav"
      sx={{
        width: 240,
        flexShrink: 0,
        display: "flex",
        flexDirection: "column",
        gap: 0.5,
        p: 2,
        borderRight: "1px solid",
        borderColor: "divider",
        bgcolor: railBg,
        backdropFilter: "blur(12px)",
        minHeight: "100%",
      }}
    >
      <Box sx={{ mb: 2, px: 0.5 }}>
        <BrandMark size="sm" showTagline={false} />
        <Typography
          variant="caption"
          sx={{
            display: "block",
            mt: 1,
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            color: "text.secondary",
            fontFamily: '"Fraunces", Georgia, serif',
          }}
        >
          Employee portal
        </Typography>
      </Box>
      {NAV.map((item) => {
        const active = isActive(item.href, item.exact);
        return (
          <Button
            key={item.href}
            component={Link}
            href={item.href}
            onClick={() => setOpen(false)}
            startIcon={item.icon}
            sx={{
              justifyContent: "flex-start",
              px: 1.5,
              py: 1,
              color: active ? accent : "text.primary",
              bgcolor: active ? `${accent}14` : "transparent",
              borderLeft: "3px solid",
              borderColor: active ? accent : "transparent",
              borderRadius: "0 8px 8px 0",
              fontWeight: active ? 700 : 500,
              "&:hover": { bgcolor: `${accent}10` },
            }}
          >
            {item.label}
          </Button>
        );
      })}
      <Box sx={{ flex: 1 }} />
      <Button
        component={Link}
        href="/dashboard"
        size="small"
        sx={{ justifyContent: "flex-start", color: "text.secondary" }}
      >
        Open full ERP
      </Button>
      <Button
        size="small"
        startIcon={<LogoutIcon />}
        onClick={doLogout}
        sx={{ justifyContent: "flex-start", color: "text.secondary" }}
      >
        Sign out
      </Button>
    </Box>
  );

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        background: isDark
          ? `radial-gradient(1200px 600px at 10% -10%, ${accent}33, transparent 55%), linear-gradient(165deg, #0A1218 0%, #121A22 48%, #0F1419 100%)`
          : `radial-gradient(1000px 520px at 8% -8%, ${accent}22, transparent 50%), linear-gradient(165deg, #E8F2F6 0%, #F4F7FA 42%, #EEF3F7 100%)`,
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          px: { xs: 1.5, md: 2 },
          py: 1,
          borderBottom: "1px solid",
          borderColor: "divider",
          bgcolor: railBg,
          backdropFilter: "blur(10px)",
        }}
      >
        <Stack direction="row" alignItems="center" spacing={1}>
          {narrow ? (
            <IconButton onClick={() => setOpen((v) => !v)} aria-label="Menu">
              {open ? <CloseIcon /> : <MenuIcon />}
            </IconButton>
          ) : null}
          <Typography
            sx={{
              fontFamily: '"Fraunces", Georgia, serif',
              fontWeight: 700,
              fontSize: { xs: "1.05rem", md: "1.2rem" },
              letterSpacing: "-0.02em",
            }}
          >
            My workplace
          </Typography>
        </Stack>
        <Stack direction="row" alignItems="center" spacing={0.5}>
          <Button
            component={Link}
            href="/guide#ess"
            target="_blank"
            rel="noopener noreferrer"
            size="small"
            sx={{ display: { xs: "none", sm: "inline-flex" }, textTransform: "none" }}
          >
            Guide
          </Button>
          <ThemeToggle />
        </Stack>
      </Box>

      <Box sx={{ display: "flex", flex: 1, minHeight: 0, position: "relative" }}>
        {!narrow ? rail : null}
        {narrow && open ? (
          <Box
            sx={{
              position: "absolute",
              inset: 0,
              zIndex: 20,
              display: "flex",
            }}
          >
            <Box sx={{ height: "100%" }}>{rail}</Box>
            <Box sx={{ flex: 1, bgcolor: "rgba(0,0,0,0.35)" }} onClick={() => setOpen(false)} />
          </Box>
        ) : null}
        <Box
          component="main"
          sx={{
            flex: 1,
            p: { xs: 2, md: 3 },
            maxWidth: 1100,
            width: "100%",
            mx: "auto",
          }}
        >
          {children}
        </Box>
      </Box>
    </Box>
  );
}
