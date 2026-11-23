"use client";

import { useEffect, useState } from "react";
import { Box, Paper, Stack, Typography } from "@mui/material";
import api from "@/lib/api";
import { formatMoney } from "@/lib/format";

type Stage = {
  stage: string;
  label: string;
  count: number;
  amount: string;
  weighted: string;
};

type ForecastMonth = {
  key: string;
  label: string;
  count: number;
  amount: string;
  weighted: string;
};

type Pipeline = {
  open_count: number;
  open_amount: string;
  weighted_amount: string;
  won_amount: string;
  lost_count: number;
  win_rate?: string | null;
  stages: Stage[];
  forecast?: ForecastMonth[];
};

export default function PipelineSummary({ refreshKey = 0 }: { refreshKey?: number }) {
  const [data, setData] = useState<Pipeline | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get<Pipeline>("/crm/opportunities/pipeline/")
      .then((res) => {
        if (!cancelled) setData(res.data);
      })
      .catch(() => {
        if (!cancelled) setData(null);
      });
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  if (!data) return null;

  const cards = [
    { label: "Open deals", value: String(data.open_count) },
    { label: "Open amount", value: formatMoney(data.open_amount) },
    { label: "Weighted forecast", value: formatMoney(data.weighted_amount) },
    { label: "Won", value: formatMoney(data.won_amount) },
    { label: "Win rate", value: data.win_rate ? `${data.win_rate}%` : "—" },
    { label: "Lost", value: String(data.lost_count) },
  ];
  const now = new Date();
  const currentKey = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  const forecast = (data.forecast || []).filter(
    (month) => month.count > 0 || month.key === currentKey
  );

  return (
    <Stack spacing={1.5} sx={{ mb: 2 }}>
      <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
        {cards.map((card) => (
          <Paper key={card.label} variant="outlined" sx={{ px: 2, py: 1.25, minWidth: 140 }}>
            <Typography variant="caption" color="text.secondary">
              {card.label}
            </Typography>
            <Typography variant="subtitle1">{card.value}</Typography>
          </Paper>
        ))}
      </Stack>
      {forecast.length > 0 ? (
        <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
          {forecast.map((month) => (
            <Box key={month.key} sx={{ minWidth: 110 }}>
              <Typography variant="caption" color="text.secondary">
                {month.label} · {month.count} · weighted
              </Typography>
              <Typography variant="body2">{formatMoney(month.weighted)}</Typography>
            </Box>
          ))}
        </Stack>
      ) : null}
      <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
        {data.stages.map((stage) => (
          <Box key={stage.stage} sx={{ minWidth: 120 }}>
            <Typography variant="caption" color="text.secondary">
              {stage.label} · {stage.count}
            </Typography>
            <Typography variant="body2">{formatMoney(stage.amount)}</Typography>
          </Box>
        ))}
      </Stack>
    </Stack>
  );
}
