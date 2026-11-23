"use client";

import { Box, Stack, Typography, useTheme } from "@mui/material";

export type NamedValue = { label: string; value: number; color?: string };

function RingCenterLabel({
  value,
  sub,
  size,
}: {
  value?: string;
  sub?: string;
  size: number;
}) {
  if (!value && !sub) return null;
  return (
    <Box
      sx={{
        position: "relative",
        zIndex: 1,
        textAlign: "center",
        lineHeight: 1,
        maxWidth: size * 0.52,
        pointerEvents: "none",
      }}
    >
      {value ? (
        <Typography
          component="div"
          sx={{
            fontSize: size >= 150 ? "1.65rem" : size >= 128 ? "1.5rem" : "1.35rem",
            fontWeight: 700,
            letterSpacing: "-0.03em",
            lineHeight: 1,
          }}
        >
          {value}
        </Typography>
      ) : null}
      {sub ? (
        <Typography
          component="div"
          variant="caption"
          color="text.secondary"
          sx={{
            display: "block",
            mt: value ? 0.5 : 0,
            lineHeight: 1.15,
            fontWeight: 500,
            letterSpacing: "0.02em",
          }}
        >
          {sub}
        </Typography>
      ) : null}
    </Box>
  );
}

export function DonutChart({
  segments,
  size = 160,
  thickness = 22,
  centerLabel,
  centerSub,
}: {
  segments: NamedValue[];
  size?: number;
  thickness?: number;
  centerLabel?: string;
  centerSub?: string;
}) {
  const theme = useTheme();
  const total = segments.reduce((s, x) => s + Math.max(0, x.value), 0) || 1;
  const r = (size - thickness) / 2;
  const c = 2 * Math.PI * r;
  let offset = 0;
  const palette = [
    theme.palette.primary.main,
    theme.palette.secondary.main,
    theme.palette.success.main,
    theme.palette.warning.main,
    "#7B8CDE",
  ];

  return (
    <Box
      sx={{
        position: "relative",
        width: size,
        height: size,
        mx: "auto",
        display: "grid",
        placeItems: "center",
      }}
    >
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        style={{ position: "absolute", inset: 0 }}
        aria-hidden
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={theme.palette.divider}
          strokeWidth={thickness}
        />
        {segments.map((seg, i) => {
          const len = (Math.max(0, seg.value) / total) * c;
          const el = (
            <circle
              key={seg.label}
              cx={size / 2}
              cy={size / 2}
              r={r}
              fill="none"
              stroke={seg.color || palette[i % palette.length]}
              strokeWidth={thickness}
              strokeDasharray={`${len} ${c - len}`}
              strokeDashoffset={-offset}
              strokeLinecap="butt"
              transform={`rotate(-90 ${size / 2} ${size / 2})`}
            />
          );
          offset += len;
          return el;
        })}
      </svg>
      <RingCenterLabel value={centerLabel} sub={centerSub} size={size} />
    </Box>
  );
}

export function BarChart({
  series,
  height = 180,
  valueKey = "value",
  color,
}: {
  series: { label: string; [k: string]: string | number }[];
  height?: number;
  valueKey?: string;
  color?: string;
}) {
  const theme = useTheme();
  const max = Math.max(1, ...series.map((s) => Number(s[valueKey] || 0)));
  const barColor = color || theme.palette.primary.main;

  return (
    <Box sx={{ height, display: "flex", alignItems: "flex-end", gap: 1, px: 0.5 }}>
      {series.map((s) => {
        const v = Number(s[valueKey] || 0);
        const h = Math.round((v / max) * (height - 28));
        return (
          <Stack key={String(s.label)} alignItems="center" spacing={0.5} sx={{ flex: 1, minWidth: 0 }}>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: 10 }}>
              {v}
            </Typography>
            <Box
              sx={{
                width: "100%",
                maxWidth: 36,
                height: Math.max(4, h),
                borderRadius: "6px 6px 2px 2px",
                bgcolor: barColor,
                opacity: 0.85,
                transition: "height 0.4s ease",
              }}
            />
            <Typography
              variant="caption"
              color="text.secondary"
              noWrap
              sx={{ fontSize: 10, maxWidth: "100%" }}
            >
              {s.label}
            </Typography>
          </Stack>
        );
      })}
    </Box>
  );
}

export function DualLineChart({
  series,
  height = 180,
}: {
  series: { label: string; journals: number; payslips: number }[];
  height?: number;
}) {
  const theme = useTheme();
  const w = 360;
  const h = height;
  const pad = { t: 12, r: 8, b: 28, l: 8 };
  const max = Math.max(
    1,
    ...series.flatMap((s) => [s.journals, s.payslips])
  );
  const innerW = w - pad.l - pad.r;
  const innerH = h - pad.t - pad.b;
  const n = Math.max(1, series.length - 1);

  const pts = (key: "journals" | "payslips") =>
    series
      .map((s, i) => {
        const x = pad.l + (i / n) * innerW;
        const y = pad.t + innerH - (s[key] / max) * innerH;
        return `${x},${y}`;
      })
      .join(" ");

  return (
    <Box sx={{ width: "100%", overflow: "hidden" }}>
      <svg viewBox={`0 0 ${w} ${h}`} width="100%" height={height} preserveAspectRatio="none">
        {[0.25, 0.5, 0.75, 1].map((p) => {
          const y = pad.t + innerH * (1 - p);
          return (
            <line
              key={p}
              x1={pad.l}
              x2={w - pad.r}
              y1={y}
              y2={y}
              stroke={theme.palette.divider}
              strokeWidth={1}
            />
          );
        })}
        <polyline
          fill="none"
          stroke={theme.palette.primary.main}
          strokeWidth={2.5}
          points={pts("journals")}
        />
        <polyline
          fill="none"
          stroke={theme.palette.secondary.main}
          strokeWidth={2.5}
          points={pts("payslips")}
        />
        {series.map((s, i) => {
          const x = pad.l + (i / n) * innerW;
          return (
            <text
              key={s.label}
              x={x}
              y={h - 8}
              textAnchor="middle"
              fill={theme.palette.text.secondary}
              fontSize={10}
            >
              {s.label}
            </text>
          );
        })}
      </svg>
      <Stack direction="row" spacing={2} justifyContent="center" sx={{ mt: 0.5 }}>
        <Stack direction="row" spacing={0.75} alignItems="center">
          <Box sx={{ width: 10, height: 10, borderRadius: 1, bgcolor: "primary.main" }} />
          <Typography variant="caption" color="text.secondary">
            Posted journals
          </Typography>
        </Stack>
        <Stack direction="row" spacing={0.75} alignItems="center">
          <Box sx={{ width: 10, height: 10, borderRadius: 1, bgcolor: "secondary.main" }} />
          <Typography variant="caption" color="text.secondary">
            Payslips
          </Typography>
        </Stack>
      </Stack>
    </Box>
  );
}

export function MeterRing({
  value,
  label,
  size = 120,
}: {
  value: number;
  label: string;
  size?: number;
}) {
  const theme = useTheme();
  const clamped = Math.max(0, Math.min(100, value));
  const r = 42;
  const c = 2 * Math.PI * r;
  const filled = (clamped / 100) * c;
  const tone =
    clamped >= 80
      ? theme.palette.success.main
      : clamped >= 55
        ? theme.palette.warning.main
        : theme.palette.error.main;

  return (
    <Box
      sx={{
        position: "relative",
        width: size,
        height: size,
        mx: "auto",
        display: "grid",
        placeItems: "center",
      }}
    >
      <svg
        width={size}
        height={size}
        viewBox="0 0 120 120"
        style={{ position: "absolute", inset: 0 }}
        aria-hidden
      >
        <circle
          cx={60}
          cy={60}
          r={r}
          fill="none"
          stroke={theme.palette.divider}
          strokeWidth={10}
        />
        <circle
          cx={60}
          cy={60}
          r={r}
          fill="none"
          stroke={tone}
          strokeWidth={10}
          strokeDasharray={`${filled} ${c - filled}`}
          strokeLinecap="round"
          transform="rotate(-90 60 60)"
        />
      </svg>
      <RingCenterLabel value={String(clamped)} sub={label} size={size} />
    </Box>
  );
}

export function LegendList({ items }: { items: NamedValue[] }) {
  const total = items.reduce((s, x) => s + x.value, 0) || 1;
  return (
    <Stack spacing={0.75} sx={{ mt: 1 }}>
      {items.map((it) => (
        <Stack
          key={it.label}
          direction="row"
          justifyContent="space-between"
          alignItems="center"
          spacing={1}
        >
          <Stack direction="row" spacing={1} alignItems="center" sx={{ minWidth: 0 }}>
            <Box
              sx={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                bgcolor: it.color || "primary.main",
                flexShrink: 0,
              }}
            />
            <Typography variant="body2" noWrap>
              {it.label}
            </Typography>
          </Stack>
          <Typography variant="body2" color="text.secondary" sx={{ flexShrink: 0 }}>
            {it.value} · {Math.round((it.value / total) * 100)}%
          </Typography>
        </Stack>
      ))}
    </Stack>
  );
}
