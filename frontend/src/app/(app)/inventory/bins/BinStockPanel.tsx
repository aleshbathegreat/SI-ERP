"use client";

import { useState } from "react";
import {
  Button,
  Paper,
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
import RelationSelect, { RELATIONS } from "@/components/crud/RelationSelect";
import { usePermissions } from "@/hooks/usePermissions";
import { useRecordAction } from "@/hooks/useRecordAction";

type Row = { item: number; item_sku: string; item_name: string; qty: string };

export default function BinStockPanel({
  binId,
  stock,
  onChanged,
}: {
  binId: string;
  stock: Row[];
  onChanged: () => void;
}) {
  const { enqueueSnackbar } = useSnackbar();
  const { canChange } = usePermissions();
  const { run, busy } = useRecordAction();
  const [item, setItem] = useState("");
  const [qty, setQty] = useState("");

  const putAway = async () => {
    if (!item || !qty) {
      enqueueSnackbar("Select an item and qty", { variant: "warning" });
      return;
    }
    const res = await run(`putaway-${binId}`, `/inventory/bins/${binId}/put-away/`, {
      body: { item: Number(item), qty },
      success: "Stock assigned to bin",
    });
    if (res) {
      setQty("");
      onChanged();
    }
  };

  return (
    <Paper variant="outlined" sx={{ p: 2, mt: 2 }}>
      <Typography variant="subtitle1" sx={{ mb: 1 }}>
        Stock in this bin
      </Typography>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>SKU</TableCell>
            <TableCell>Item</TableCell>
            <TableCell align="right">Qty</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {stock.length === 0 ? (
            <TableRow>
              <TableCell colSpan={3}>No stock assigned yet.</TableCell>
            </TableRow>
          ) : (
            stock.map((r) => (
              <TableRow key={r.item}>
                <TableCell>{r.item_sku}</TableCell>
                <TableCell>{r.item_name}</TableCell>
                <TableCell align="right">{r.qty}</TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
      {canChange("inventory.bins") ? (
        <Stack spacing={2} sx={{ mt: 2 }}>
          <Typography variant="subtitle2">Put away (assign warehouse stock to this bin)</Typography>
          <RelationSelect
            label="Item"
            value={item}
            onChange={setItem}
            relation={RELATIONS.item}
          />
          <TextField
            label="Qty"
            type="number"
            value={qty}
            onChange={(e) => setQty(e.target.value)}
          />
          <Button variant="contained" disabled={busy} onClick={() => void putAway()}>
            Put away
          </Button>
        </Stack>
      ) : null}
    </Paper>
  );
}
