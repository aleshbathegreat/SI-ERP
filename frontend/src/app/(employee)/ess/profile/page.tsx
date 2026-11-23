"use client";

import { useEffect, useState } from "react";
import {
  Alert,
  Avatar,
  Box,
  Button,
  CircularProgress,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import EssSection, { EssPanel } from "@/components/ess/EssSection";
import { EssEmployee, fetchEssProfile, patchEssProfile, uploadEssPhoto } from "@/lib/essApi";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";
import { useSnackbar } from "notistack";

function maskId(value?: string) {
  const text = (value || "").trim();
  if (!text) return "—";
  if (text.length <= 4) return "••••";
  return `••••${text.slice(-4)}`;
}

function ReadRow({ label, value }: { label: string; value?: string | null }) {
  return (
    <Stack direction="row" justifyContent="space-between" spacing={2} sx={{ py: 0.75 }}>
      <Typography variant="body2" color="text.secondary">{label}</Typography>
      <Typography variant="body2" fontWeight={600} sx={{ textAlign: "right" }}>
        {value || "—"}
      </Typography>
    </Stack>
  );
}

export default function EssProfilePage() {
  const { enqueueSnackbar } = useSnackbar();
  const [emp, setEmp] = useState<EssEmployee | null>(null);
  const [tab, setTab] = useState(0);
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [address, setAddress] = useState("");
  const [emergencyName, setEmergencyName] = useState("");
  const [emergencyPhone, setEmergencyPhone] = useState("");
  const [bankName, setBankName] = useState("");
  const [bankIban, setBankIban] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  const fill = (p: EssEmployee) => {
    setEmp(p);
    setPhone(p.phone || "");
    setEmail(p.email || "");
    setAddress(p.address || "");
    setEmergencyName(p.emergency_contact_name || "");
    setEmergencyPhone(p.emergency_contact_phone || "");
    setBankName(p.bank_name || "");
    setBankIban(p.bank_iban || "");
  };

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        fill(await fetchEssProfile());
      } catch (e: unknown) {
        setErr(getApiErrorMessage(e, "Could not load profile"));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      fill(
        await patchEssProfile({
          phone,
          email,
          address,
          emergency_contact_name: emergencyName,
          emergency_contact_phone: emergencyPhone,
          bank_name: bankName,
          bank_iban: bankIban,
        }),
      );
      enqueueSnackbar("Profile updated", { variant: "success" });
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, "Could not save"), errorSnackbarOpts);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: "grid", placeItems: "center", minHeight: 240 }}>
        <CircularProgress size={32} />
      </Box>
    );
  }

  const name =
    emp?.full_name ||
    [emp?.first_name, emp?.last_name].filter(Boolean).join(" ") ||
    "—";

  return (
    <EssSection title="Profile" subtitle="Your record. Contact, address, and bank details can be updated here.">
      {err ? <Alert severity="error" sx={{ mb: 2 }}>{err}</Alert> : null}
      <EssPanel>
        <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 1 }}>
          <Avatar src={emp?.photo || undefined} sx={{ width: 64, height: 64, fontSize: "1.4rem" }}>
            {name.slice(0, 1)}
          </Avatar>
          <Box>
            <Typography sx={{ fontFamily: '"Fraunces", Georgia, serif', fontWeight: 700, fontSize: "1.45rem" }}>
              {name}
            </Typography>
            <Button component="label" size="small">
              Upload photo
              <input
                hidden
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  e.target.value = "";
                  if (!file) return;
                  setSaving(true);
                  try {
                    fill(await uploadEssPhoto(file));
                    enqueueSnackbar("Photo updated", { variant: "success" });
                  } catch (error: unknown) {
                    enqueueSnackbar(getApiErrorMessage(error, "Could not upload the photo"), errorSnackbarOpts);
                  } finally {
                    setSaving(false);
                  }
                }}
              />
            </Button>
          </Box>
        </Stack>
        <Typography color="text.secondary" sx={{ mb: 2, mt: 1 }}>
          {[emp?.designation_title, emp?.employee_code, emp?.department_name].filter(Boolean).join(" · ") || "—"}
        </Typography>
        <Tabs
          value={tab}
          onChange={(_, next) => setTab(next)}
          variant="scrollable"
          scrollButtons="auto"
          sx={{ mb: 2, borderBottom: 1, borderColor: "divider" }}
        >
          <Tab label="Contact" />
          <Tab label="Employment" />
          <Tab label="Personal" />
          <Tab label="Address" />
          <Tab label="Bank" />
        </Tabs>
        {tab === 0 ? (
          <Stack spacing={1.5} sx={{ maxWidth: 480 }}>
            <TextField label="Official email" value={email} onChange={(e) => setEmail(e.target.value)} />
            <TextField label="Phone" value={phone} onChange={(e) => setPhone(e.target.value)} />
          </Stack>
        ) : null}
        {tab === 1 ? (
          <Box sx={{ maxWidth: 520 }}>
            <ReadRow label="Department" value={emp?.department_name} />
            <ReadRow label="Designation" value={emp?.designation_title} />
            <ReadRow label="Shift" value={emp?.shift_name} />
            <ReadRow label="Location" value={emp?.work_location} />
            <ReadRow label="Manager" value={emp?.reporting_manager_name} />
            <ReadRow label="Joined" value={emp?.date_of_joining} />
            <ReadRow label="Contract" value={emp?.contract_type} />
            <ReadRow label="Status" value={emp?.status} />
          </Box>
        ) : null}
        {tab === 2 ? (
          <Box sx={{ maxWidth: 520 }}>
            <ReadRow label="Date of birth" value={emp?.date_of_birth} />
            <ReadRow label="Gender" value={emp?.gender} />
            <ReadRow label="Nationality" value={emp?.nationality} />
            <ReadRow label="Marital status" value={emp?.marital_status} />
            <ReadRow label="National ID" value={maskId(emp?.national_id)} />
          </Box>
        ) : null}
        {tab === 3 ? (
          <Stack spacing={1.5} sx={{ maxWidth: 480 }}>
            <TextField label="Address" value={address} onChange={(e) => setAddress(e.target.value)} multiline minRows={2} />
            <TextField label="Emergency contact" value={emergencyName} onChange={(e) => setEmergencyName(e.target.value)} />
            <TextField label="Emergency phone" value={emergencyPhone} onChange={(e) => setEmergencyPhone(e.target.value)} />
          </Stack>
        ) : null}
        {tab === 4 ? (
          <Stack spacing={1.5} sx={{ maxWidth: 480 }}>
            <TextField label="Bank" value={bankName} onChange={(e) => setBankName(e.target.value)} />
            <TextField label="IBAN" value={bankIban} onChange={(e) => setBankIban(e.target.value)} />
          </Stack>
        ) : null}
        {tab !== 1 && tab !== 2 ? (
          <Button variant="contained" disabled={saving} onClick={save} sx={{ mt: 2 }}>
            Save
          </Button>
        ) : null}
      </EssPanel>
    </EssSection>
  );
}
