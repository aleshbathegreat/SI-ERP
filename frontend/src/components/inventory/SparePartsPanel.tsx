"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Button,
  MenuItem,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { useSnackbar } from "notistack";
import { DetailSection } from "@/components/crud/DetailPageShell";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { listResource } from "@/lib/crudApi";

type PartLine = {
  id: number;
  item_sku?: string;
  item_name?: string;
  qty?: string;
  unit_cost?: string;
  unit_price?: string;
  warehouse_code?: string;
};

type Option = { id: number; sku?: string; name?: string; code?: string; item_type?: string };

export default function SparePartsPanel({
  lines,
  canIssue,
  issueUrl,
  onChanged,
  showPrice = false,
  canInvoice = false,
  invoiceUrl,
  invoiceId,
  invoiceNo,
}: {
  lines: PartLine[];
  canIssue: boolean;
  issueUrl: string;
  onChanged: () => void;
  showPrice?: boolean;
  canInvoice?: boolean;
  invoiceUrl?: string;
  invoiceId?: number | null;
  invoiceNo?: string;
}) {
  const { enqueueSnackbar } = useSnackbar();
  const [items, setItems] = useState<Option[]>([]);
  const [warehouses, setWarehouses] = useState<Option[]>([]);
  const [itemId, setItemId] = useState("");
  const [warehouseId, setWarehouseId] = useState("");
  const [qty, setQty] = useState("1");
  const [labor, setLabor] = useState("");
  const [busy, setBusy] = useState(false);
  const [query, setQuery] = useState("");

  const loadItems = async (search?: string) => {
    const rows = await listResource<Option>("/inventory/items/", {
      search: search || undefined,
    });
    setItems(rows.filter((r) => r.item_type !== "service"));
  };

  useEffect(() => {
    void loadItems().catch(() => setItems([]));
    void listResource<Option>("/inventory/warehouses/")
      .then(setWarehouses)
      .catch(() => setWarehouses([]));
  }, []);

  const issue = async () => {
    setBusy(true);
    try {
      await api.post(issueUrl, {
        item: Number(itemId),
        qty,
        ...(warehouseId ? { warehouse: Number(warehouseId) } : {}),
      });
      enqueueSnackbar("Part issued from stock", { variant: "success" });
      setQty("1");
      onChanged();
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Could not issue part"), errorSnackbarOpts);
    } finally {
      setBusy(false);
    }
  };

  const invoice = async () => {
    if (!invoiceUrl) return;
    setBusy(true);
    try {
      const { data } = await api.post(invoiceUrl, {
        ...(labor ? { labor_amount: labor } : {}),
      });
      enqueueSnackbar(
        data.invoice_no ? `Draft invoice ${data.invoice_no} created` : "Draft invoice created",
        { variant: "success" }
      );
      onChanged();
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Could not create invoice"), errorSnackbarOpts);
    } finally {
      setBusy(false);
    }
  };

  return (
    <DetailSection title="Spare parts">
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>SKU</TableCell>
            <TableCell>Item</TableCell>
            <TableCell>Warehouse</TableCell>
            <TableCell align="right">Qty</TableCell>
            <TableCell align="right">Cost</TableCell>
            {showPrice ? <TableCell align="right">Price</TableCell> : null}
          </TableRow>
        </TableHead>
        <TableBody>
          {lines.length === 0 ? (
            <TableRow>
              <TableCell colSpan={showPrice ? 6 : 5}>
                <Typography variant="body2" color="text.secondary">
                  No parts issued
                </Typography>
              </TableCell>
            </TableRow>
          ) : (
            lines.map((ln) => (
              <TableRow key={ln.id}>
                <TableCell>{ln.item_sku}</TableCell>
                <TableCell>{ln.item_name}</TableCell>
                <TableCell>{ln.warehouse_code || "—"}</TableCell>
                <TableCell align="right">{ln.qty}</TableCell>
                <TableCell align="right">{ln.unit_cost}</TableCell>
                {showPrice ? <TableCell align="right">{ln.unit_price}</TableCell> : null}
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
      {canIssue ? (
        <Stack direction="row" spacing={1} sx={{ mt: 1.5 }} flexWrap="wrap" useFlexGap>
          <TextField
            size="small"
            label="Find item"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void loadItems(query);
            }}
          />
          <Button size="small" onClick={() => void loadItems(query)}>
            Search
          </Button>
          <TextField
            select
            size="small"
            label="Item"
            value={itemId}
            onChange={(e) => setItemId(e.target.value)}
            sx={{ minWidth: 200 }}
          >
            <MenuItem value="">Select</MenuItem>
            {items.map((it) => (
              <MenuItem key={it.id} value={String(it.id)}>
                {it.sku} · {it.name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            size="small"
            label="Warehouse"
            value={warehouseId}
            onChange={(e) => setWarehouseId(e.target.value)}
            sx={{ minWidth: 140 }}
          >
            <MenuItem value="">Default</MenuItem>
            {warehouses.map((w) => (
              <MenuItem key={w.id} value={String(w.id)}>
                {w.code || w.name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            size="small"
            label="Qty"
            value={qty}
            onChange={(e) => setQty(e.target.value)}
            sx={{ width: 90 }}
          />
          <Button variant="contained" disabled={busy || !itemId} onClick={() => void issue()}>
            Issue
          </Button>
        </Stack>
      ) : null}
      {invoiceId ? (
        <Button
          component={Link}
          href={`/sales/invoices/${invoiceId}`}
          sx={{ mt: 1.5 }}
          size="small"
        >
          {invoiceNo || "AR invoice"}
        </Button>
      ) : canInvoice && invoiceUrl ? (
        <Stack direction="row" spacing={1} sx={{ mt: 1.5 }} alignItems="center">
          <TextField
            size="small"
            label="Labor amount"
            value={labor}
            onChange={(e) => setLabor(e.target.value)}
            sx={{ width: 140 }}
          />
          <Button variant="outlined" disabled={busy} onClick={() => void invoice()}>
            Create AR invoice
          </Button>
        </Stack>
      ) : null}
    </DetailSection>
  );
}
