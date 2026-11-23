"use client";

import Link from "next/link";
import {
  Chip,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import FormPageShell from "@/components/crud/FormPageShell";
import { DetailSection } from "@/components/crud/DetailPageShell";
import ModuleGate from "@/components/ModuleGate";
import { useEntityForm } from "@/hooks/useEntityForm";
import { useParams } from "next/navigation";
import { formatMoney } from "@/lib/format";

const moduleKey = "sales.deliveries";
const basePath = "/sales/deliveries";
const resourcePath = "/sales/deliveries/";

type DnLine = {
  id?: number;
  item_sku?: string;
  item_name?: string;
  description?: string;
  qty?: string | number;
  unit_price?: string | number;
  line_total?: string;
};

type DnForm = {
  dn_no: string;
  status: string;
  delivery_date: string;
  customer_name: string;
  order_no: string;
  sales_order: string;
  warehouse_name: string;
  notes: string;
  total: string;
  lines: DnLine[];
};

export default function DnDetail() {
  const params = useParams();
  const id = String(params.id);

  const { form, loading } = useEntityForm<DnForm>({
    resourcePath,
    entityLabel: "Delivery note",
    basePath,
    mode: "view",
    id,
    empty: {
      dn_no: "",
      status: "",
      delivery_date: "",
      customer_name: "",
      order_no: "",
      sales_order: "",
      warehouse_name: "",
      notes: "",
      total: "0",
      lines: [],
    },
    mapLoaded: (row) => ({
      dn_no: String(row.dn_no ?? ""),
      status: String(row.status ?? ""),
      delivery_date: String(row.delivery_date ?? ""),
      customer_name: String(row.customer_name ?? ""),
      order_no: String(row.order_no ?? ""),
      sales_order: row.sales_order != null ? String(row.sales_order) : "",
      warehouse_name: String(row.warehouse_name ?? ""),
      notes: String(row.notes ?? ""),
      total: String(row.total ?? "0"),
      lines: Array.isArray(row.lines) ? (row.lines as DnLine[]) : [],
    }),
  });

  return (
    <ModuleGate module={moduleKey}>
      <FormPageShell
        title={form.dn_no || "Delivery note"}
        subtitle="Posted outbound dispatch (read-only)"
        backHref={basePath}
        mode="view"
        loading={loading}
        extraActions={
          form.sales_order ? (
            <Chip
              component={Link}
              href={`/sales/orders/${form.sales_order}`}
              clickable
              label={`SO ${form.order_no || form.sales_order}`}
              size="small"
              variant="outlined"
            />
          ) : null
        }
      >
        <Stack spacing={2}>
          <DetailSection title="Header">
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
              <Chip size="small" label={form.status || "—"} variant="outlined" />
              <Typography variant="body2" color="text.secondary">
                {form.delivery_date || "—"}
              </Typography>
            </Stack>
            <Typography variant="body2">
              Customer: <strong>{form.customer_name || "—"}</strong>
            </Typography>
            <Typography variant="body2">
              Warehouse: <strong>{form.warehouse_name || "—"}</strong>
            </Typography>
            {form.notes ? (
              <Typography variant="body2" sx={{ mt: 1 }} color="text.secondary">
                {form.notes}
              </Typography>
            ) : null}
            <Typography variant="subtitle2" sx={{ mt: 1.5 }}>
              Total {formatMoney(form.total)}
            </Typography>
          </DetailSection>
          <DetailSection title="Lines">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>SKU</TableCell>
                  <TableCell>Item</TableCell>
                  <TableCell align="right">Qty</TableCell>
                  <TableCell align="right">Price</TableCell>
                  <TableCell align="right">Line</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {(form.lines || []).length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5}>
                      <Typography variant="body2" color="text.secondary">
                        No lines
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  form.lines.map((ln, idx) => (
                    <TableRow key={ln.id ?? idx}>
                      <TableCell>{ln.item_sku || "—"}</TableCell>
                      <TableCell>{ln.item_name || ln.description || "—"}</TableCell>
                      <TableCell align="right">{String(ln.qty ?? "—")}</TableCell>
                      <TableCell align="right">
                        {formatMoney(String(ln.unit_price ?? "0"))}
                      </TableCell>
                      <TableCell align="right">
                        {formatMoney(String(ln.line_total ?? "0"))}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </DetailSection>
        </Stack>
      </FormPageShell>
    </ModuleGate>
  );
}
