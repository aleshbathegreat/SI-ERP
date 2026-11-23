"use client";

import { IconButton, Tooltip } from "@mui/material";
import DarkModeOutlinedIcon from "@mui/icons-material/DarkModeOutlined";
import LightModeOutlinedIcon from "@mui/icons-material/LightModeOutlined";
import { useColorMode } from "@/theme/ColorModeContext";

type Props = {
  size?: "small" | "medium" | "large";
};

export default function ThemeToggle({ size = "medium" }: Props) {
  const { mode, toggleColorMode } = useColorMode();
  const isDark = mode === "dark";

  return (
    <Tooltip title={isDark ? "Switch to light mode" : "Switch to dark mode"}>
      <IconButton
        onClick={toggleColorMode}
        color="inherit"
        size={size}
        aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      >
        {isDark ? <LightModeOutlinedIcon /> : <DarkModeOutlinedIcon />}
      </IconButton>
    </Tooltip>
  );
}
