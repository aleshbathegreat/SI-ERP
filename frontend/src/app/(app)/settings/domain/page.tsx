"use client";

import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import ModuleGate from "@/components/ModuleGate";
import PageHeader from "@/components/PageHeader";
import BrandMark from "@/components/BrandMark";
import { useBranding } from "@/components/BrandingProvider";
import api from "@/lib/api";
import { useSnackbar } from "notistack";
import { usePermissions } from "@/hooks/usePermissions";
import { useAppDispatch } from "@/store/hooks";
import { setOrganization } from "@/store/auth/slice";

type DomainInfo = {
  organization: string;
  name: string;
  brand_name: string;
  brand_tagline?: string;
  brand_primary_color: string;
  brand_secondary_color?: string;
  brand_logo_url?: string | null;
  brand_logo_dark_url?: string | null;
  brand_favicon_url?: string | null;
  subdomain: string | null;
  platform_root: string | null;
  custom_domain: string;
  custom_domain_verified: boolean;
  domain_verify_token: string;
  dns_instructions: {
    cname: { host: string; target: string };
    txt: { host: string; value: string };
  };
};

export default function TenantDomainPage() {
  const { canChange } = usePermissions();
  const { enqueueSnackbar } = useSnackbar();
  const { setBranding, refresh } = useBranding();
  const dispatch = useAppDispatch();
  const [info, setInfo] = useState<DomainInfo | null>(null);
  const [brandName, setBrandName] = useState("");
  const [tagline, setTagline] = useState("");
  const [color, setColor] = useState("#1B6A94");
  const [secondary, setSecondary] = useState("#C45C26");
  const [domain, setDomain] = useState("");
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [logoDarkFile, setLogoDarkFile] = useState<File | null>(null);
  const [faviconFile, setFaviconFile] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [msg, setMsg] = useState("");

  const load = async () => {
    const { data } = await api.get<DomainInfo>("/settings/domain/");
    setInfo(data);
    setBrandName(data.brand_name || "");
    setTagline(data.brand_tagline || "");
    setColor(data.brand_primary_color || "#1B6A94");
    setSecondary(data.brand_secondary_color || "#C45C26");
    setDomain(data.custom_domain || "");
    setBranding({
      mode: "tenant",
      name: data.name,
      code: data.organization,
      brand_name: data.brand_name,
      brand_tagline: data.brand_tagline,
      brand_primary_color: data.brand_primary_color,
      brand_secondary_color: data.brand_secondary_color,
      brand_logo_url: data.brand_logo_url,
      brand_logo_dark_url: data.brand_logo_dark_url,
      brand_favicon_url: data.brand_favicon_url,
    });
  };

  useEffect(() => {
    load().catch(() => undefined);
  }, []);

  const save = async () => {
    setSaving(true);
    setMsg("");
    try {
      const fd = new FormData();
      fd.append("brand_name", brandName);
      fd.append("brand_tagline", tagline);
      fd.append("brand_primary_color", color);
      fd.append("brand_secondary_color", secondary);
      fd.append("custom_domain", domain);
      if (logoFile) fd.append("brand_logo", logoFile);
      if (logoDarkFile) fd.append("brand_logo_dark", logoDarkFile);
      if (faviconFile) fd.append("brand_favicon", faviconFile);
      const { data } = await api.put("/settings/domain/", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      enqueueSnackbar("Branding saved", { variant: "success" });
      setLogoFile(null);
      setLogoDarkFile(null);
      setFaviconFile(null);
      await load();
      await refresh();
      // refresh org in auth store for shell
      try {
        const me = await api.get("/auth/me/");
        if (me.data?.organization) {
          dispatch(setOrganization(me.data.organization));
          localStorage.setItem("organization", JSON.stringify(me.data.organization));
        }
      } catch {
        /* optional */
      }
      setInfo(data);
    } catch (e: unknown) {
      const detail =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Save failed";
      enqueueSnackbar(String(detail), { variant: "error" });
    } finally {
      setSaving(false);
    }
  };

  return (
    <ModuleGate module="settings.domain">
      <PageHeader
        title="Domain & branding"
        subtitle="Logo, colors, and custom domain — applied across login and the app shell"
      />

      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            Live preview
          </Typography>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            spacing={3}
            alignItems="center"
            sx={{
              p: 2,
              borderRadius: 2,
              border: "1px dashed",
              borderColor: "divider",
              bgcolor: "background.default",
            }}
          >
            <BrandMark size="lg" showTagline />
            {info?.brand_logo_url ? (
              <Box
                component="img"
                src={info.brand_logo_url}
                alt="logo"
                sx={{ height: 48, objectFit: "contain" }}
              />
            ) : null}
          </Stack>
        </CardContent>
      </Card>

      {info?.subdomain ? (
        <Alert severity="success" sx={{ mb: 2 }}>
          Platform subdomain: <strong>{info.subdomain}</strong>
        </Alert>
      ) : (
        <Alert severity="info" sx={{ mb: 2 }}>
          Set <code>PLATFORM_ROOT_DOMAIN</code> for automatic tenant subdomains. Custom domains
          work either way.
        </Alert>
      )}

      {msg ? (
        <Alert severity="info" sx={{ mb: 2 }}>
          {msg}
        </Alert>
      ) : null}

      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Brand identity
          </Typography>
          <Stack spacing={1.5} maxWidth={560}>
            <TextField
              label="Brand name"
              value={brandName}
              disabled={!canChange("settings.domain")}
              onChange={(e) => setBrandName(e.target.value)}
              helperText="Shown in sidebar, login, and browser tab"
            />
            <TextField
              label="Tagline"
              value={tagline}
              disabled={!canChange("settings.domain")}
              onChange={(e) => setTagline(e.target.value)}
              helperText="Short supporting line under the brand"
            />
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
              <TextField
                label="Primary color"
                value={color}
                disabled={!canChange("settings.domain")}
                onChange={(e) => setColor(e.target.value)}
                helperText="Theme + login accent"
                fullWidth
              />
              <TextField
                label="Secondary color"
                value={secondary}
                disabled={!canChange("settings.domain")}
                onChange={(e) => setSecondary(e.target.value)}
                fullWidth
              />
            </Stack>
            <Box>
              <Typography variant="body2" gutterBottom>
                Logo (light UI) — PNG/SVG, transparent preferred
              </Typography>
              <Button variant="outlined" component="label" disabled={!canChange("settings.domain")}>
                {logoFile ? logoFile.name : info?.brand_logo_url ? "Replace logo" : "Upload logo"}
                <input
                  hidden
                  type="file"
                  accept="image/png,image/jpeg,image/webp,image/svg+xml"
                  onChange={(e) => setLogoFile(e.target.files?.[0] || null)}
                />
              </Button>
            </Box>
            <Box>
              <Typography variant="body2" gutterBottom>
                Logo (dark UI) — optional
              </Typography>
              <Button variant="outlined" component="label" disabled={!canChange("settings.domain")}>
                {logoDarkFile
                  ? logoDarkFile.name
                  : info?.brand_logo_dark_url
                    ? "Replace dark logo"
                    : "Upload dark logo"}
                <input
                  hidden
                  type="file"
                  accept="image/png,image/jpeg,image/webp,image/svg+xml"
                  onChange={(e) => setLogoDarkFile(e.target.files?.[0] || null)}
                />
              </Button>
            </Box>
            <Box>
              <Typography variant="body2" gutterBottom>
                Favicon
              </Typography>
              <Button variant="outlined" component="label" disabled={!canChange("settings.domain")}>
                {faviconFile
                  ? faviconFile.name
                  : info?.brand_favicon_url
                    ? "Replace favicon"
                    : "Upload favicon"}
                <input
                  hidden
                  type="file"
                  accept="image/png,image/x-icon,image/svg+xml,image/webp"
                  onChange={(e) => setFaviconFile(e.target.files?.[0] || null)}
                />
              </Button>
            </Box>
          </Stack>
        </CardContent>
      </Card>

      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Custom domain
          </Typography>
          <Alert
            severity={info?.custom_domain_verified ? "success" : "warning"}
            sx={{ mb: 2 }}
          >
            {info?.custom_domain_verified
              ? `Verified: ${info.custom_domain}`
              : "Point DNS, then Verify. Unverified domains still resolve for setup."}
          </Alert>
          <Stack spacing={1.5} maxWidth={560}>
            <TextField
              label="Custom hostname"
              placeholder="erp.yourcompany.com"
              value={domain}
              disabled={!canChange("settings.domain")}
              onChange={(e) => setDomain(e.target.value)}
            />
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              <Button
                variant="contained"
                disabled={!canChange("settings.domain") || saving}
                onClick={save}
              >
                {saving ? "Saving…" : "Save branding & domain"}
              </Button>
              <Button
                variant="outlined"
                disabled={!canChange("settings.domain") || verifying || !domain}
                onClick={async () => {
                  setVerifying(true);
                  setMsg("");
                  try {
                    const { data } = await api.post("/settings/domain/verify/", {});
                    setMsg(data.detail || "Verified");
                    enqueueSnackbar("Domain verified", { variant: "success" });
                    await load();
                  } catch (e: unknown) {
                    const detail =
                      (e as { response?: { data?: { detail?: string } } })?.response?.data
                        ?.detail || "Verification failed";
                    setMsg(String(detail));
                    enqueueSnackbar(String(detail), { variant: "error" });
                  } finally {
                    setVerifying(false);
                  }
                }}
              >
                {verifying ? "Checking DNS…" : "Verify DNS"}
              </Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      {info?.dns_instructions ? (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              DNS instructions
            </Typography>
            <Typography variant="body2" paragraph>
              Option A — CNAME: <code>{info.dns_instructions.cname.host}</code> →{" "}
              <code>{info.dns_instructions.cname.target}</code>
            </Typography>
            <Typography variant="body2" paragraph>
              Option B — TXT: <code>{info.dns_instructions.txt.host}</code> ={" "}
              <code>{info.dns_instructions.txt.value}</code>
            </Typography>
          </CardContent>
        </Card>
      ) : null}
    </ModuleGate>
  );
}
