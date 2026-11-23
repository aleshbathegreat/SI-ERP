"use client";

import { useEffect, useState } from "react";
import {
  Box,
  CircularProgress,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import ModuleGate from "@/components/ModuleGate";
import api from "@/lib/api";
import { formatMoney } from "@/lib/format";

type CustomerRow = {
  customer_id: number;
  customer_code: string;
  customer_name: string;
  current: string;
  "1_30": string;
  "31_60": string;
  "61_90": string;
  "90_plus": string;
  total: string;
};

type AgingResp = {
  as_of: string;
  customers: CustomerRow[];
  totals: Record<string, string>;
};

const moduleKey = "sales.credit";

export default function CreditAgingPage() {
  const [data, setData] = useState<AgingResp | null>(null);
  const [loading, setLoading] = useState(true);
  const [asOf, setAsOf] = useState(new Date().toISOString().slice(0, 10));

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const { data: resp } = await api.get<AgingResp>("/sales/invoices/aging/", {
          params: { as_of: asOf },
        });
        if (!cancelled) setData(resp);
      } catch {
        if (!cancelled) setData(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [asOf]);

  const totals = data?.totals;

  return (
    <ModuleGate module={moduleKey}>
      <Box>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems="center" sx={{ mb: 2 }}>
          <Box sx={{ flex: 1 }}>
            <Typography variant="h5" fontWeight={700}>
              AR credit aging
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Open invoices by customer · current / 1–30 / 31–60 / 61–90 / 90+
            </Typography>
          </Box>
          <TextField
            size="small"
            type="date"
            label="As of"
            InputLabelProps={{ shrink: true }}
            value={asOf}
            onChange={(e) => setAsOf(e.target.value)}
          />
        </Stack>
        {loading ? (
          <CircularProgress size={28} />
        ) : !data ? (
          <Typography color="text.secondary">Could not load aging report.</Typography>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Customer</TableCell>
                <TableCell align="right">Current</TableCell>
                <TableCell align="right">1–30</TableCell>
                <TableCell align="right">31–60</TableCell>
                <TableCell align="right">61–90</TableCell>
                <TableCell align="right">90+</TableCell>
                <TableCell align="right">Total</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(data.customers || []).length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7}>
                    <Typography variant="body2" color="text.secondary">
                      No open AR invoices as of {data.as_of}
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                <>
                  {data.customers.map((r) => (
                    <TableRow key={r.customer_id}>
                      <TableCell>
                        {r.customer_code} · {r.customer_name}
                      </TableCell>
                      <TableCell align="right">{formatMoney(r.current)}</TableCell>
                      <TableCell align="right">{formatMoney(r["1_30"])}</TableCell>
                      <TableCell align="right">{formatMoney(r["31_60"])}</TableCell>
                      <TableCell align="right">{formatMoney(r["61_90"])}</TableCell>
                      <TableCell align="right">{formatMoney(r["90_plus"])}</TableCell>
                      <TableCell align="right">{formatMoney(r.total)}</TableCell>
                    </TableRow>
                  ))}
                  {totals ? (
                    <TableRow>
                      <TableCell>
                        <strong>Totals</strong>
                      </TableCell>
                      <TableCell align="right">
                        <strong>{formatMoney(totals.current)}</strong>
                      </TableCell>
                      <TableCell align="right">
                        <strong>{formatMoney(totals["1_30"])}</strong>
                      </TableCell>
                      <TableCell align="right">
                        <strong>{formatMoney(totals["31_60"])}</strong>
                      </TableCell>
                      <TableCell align="right">
                        <strong>{formatMoney(totals["61_90"])}</strong>
                      </TableCell>
                      <TableCell align="right">
                        <strong>{formatMoney(totals["90_plus"])}</strong>
                      </TableCell>
                      <TableCell align="right">
                        <strong>{formatMoney(totals.total)}</strong>
                      </TableCell>
                    </TableRow>
                  ) : null}
                </>
              )}
            </TableBody>
          </Table>
        )}
      </Box>
    </ModuleGate>
  );
}
