"use client";

import { useEffect, useState } from "react";
import {
  Box,
  Chip,
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

type Row = {
  id: number;
  warehouse_name?: string;
  warehouse_code?: string;
  item_sku?: string;
  item_name?: string;
  qty: string | number;
};

const moduleKey = "inventory.items";

export default function StockLevelsPage() {
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const { data } = await api.get("/inventory/stock-levels/", {
          params: q ? { search: q } : undefined,
        });
        const list = Array.isArray(data) ? data : data?.results || [];
        if (!cancelled) setRows(list);
      } catch {
        if (!cancelled) setRows([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [q]);

  return (
    <ModuleGate module={moduleKey}>
      <Box>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems="center" sx={{ mb: 2 }}>
          <Box sx={{ flex: 1 }}>
            <Typography variant="h5" fontWeight={700}>
              Stock levels
            </Typography>
            <Typography variant="body2" color="text.secondary">
              On-hand by warehouse · from StockLevel API
            </Typography>
          </Box>
          <TextField
            size="small"
            label="Search SKU / warehouse"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            sx={{ minWidth: 240 }}
          />
        </Stack>
        {loading ? (
          <CircularProgress size={28} />
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Warehouse</TableCell>
                <TableCell>SKU</TableCell>
                <TableCell>Item</TableCell>
                <TableCell align="right">Qty</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4}>
                    <Typography variant="body2" color="text.secondary">
                      No stock levels
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                rows.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell>
                      {r.warehouse_name || r.warehouse_code || "—"}
                    </TableCell>
                    <TableCell>{r.item_sku || "—"}</TableCell>
                    <TableCell>{r.item_name || "—"}</TableCell>
                    <TableCell align="right">
                      <Chip size="small" label={String(r.qty)} variant="outlined" />
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        )}
      </Box>
    </ModuleGate>
  );
}
