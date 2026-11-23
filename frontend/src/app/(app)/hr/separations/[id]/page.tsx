"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Stack,
  Typography,
} from "@mui/material";
import EntityFormRoute from "@/components/crud/EntityFormRoute";
import ModuleGate from "@/components/ModuleGate";
import { getEntityDef } from "@/lib/entityCrudDefs";
import api from "@/lib/api";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { useSnackbar } from "notistack";

const def = getEntityDef("hr/separations")!;

type FnF = {
  leave_encashment?: string | number;
  notice_pay?: string | number;
  gratuity?: string | number;
  deductions?: string | number;
  net_payable?: string | number;
  status?: string;
  notes?: string;
};

export default function Page() {
  const params = useParams();
  const id = String(params.id);
  const { enqueueSnackbar } = useSnackbar();
  const [fnf, setFnf] = useState<FnF | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get(`/hr/separations/${id}/`);
      setFnf((data?.fnf_worksheet as FnF) || null);
    } catch {
      setFnf(null);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const calculate = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/hr/separations/${id}/calculate/`, {});
      setFnf((data?.fnf_worksheet as FnF) || null);
      enqueueSnackbar("F&F worksheet calculated", { variant: "success" });
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Calculate failed"), errorSnackbarOpts);
    } finally {
      setBusy(false);
    }
  };

  return (
    <ModuleGate module="hr.separation">
      <EntityFormRoute
        moduleKey={def.moduleKey}
        resourcePath={def.apiPath}
        entityLabel={def.entityLabel}
        basePath={`/${def.route}`}
        mode="view"
        id={id}
        fields={def.fields}
        empty={def.empty}
      />
      <Box sx={{ mt: 3, p: 2, border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}>
          <Typography variant="h6">Full &amp; final worksheet</Typography>
          <Button variant="contained" onClick={calculate} disabled={busy}>
            {busy ? "Calculating…" : "Calculate"}
          </Button>
        </Stack>
        {loading ? (
          <CircularProgress size={24} />
        ) : !fnf ? (
          <Alert severity="info">No worksheet yet — click Calculate to create one.</Alert>
        ) : (
          <Stack spacing={0.5}>
            <Typography variant="body2">Status: {fnf.status || "—"}</Typography>
            <Typography variant="body2">Leave encashment: {fnf.leave_encashment ?? 0}</Typography>
            <Typography variant="body2">Notice pay: {fnf.notice_pay ?? 0}</Typography>
            <Typography variant="body2">Gratuity: {fnf.gratuity ?? 0}</Typography>
            <Typography variant="body2">Deductions: {fnf.deductions ?? 0}</Typography>
            <Typography variant="subtitle1" fontWeight={700}>
              Net payable: {fnf.net_payable ?? 0}
            </Typography>
          </Stack>
        )}
      </Box>
    </ModuleGate>
  );
}
