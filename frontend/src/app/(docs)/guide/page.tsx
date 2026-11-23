"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Box,
  Button,
  Chip,
  Divider,
  GlobalStyles,
  InputAdornment,
  List,
  ListItemButton,
  ListItemText,
  Paper,
  Stack,
  Step,
  StepContent,
  StepLabel,
  Stepper,
  TextField,
  Typography,
} from "@mui/material";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import SearchIcon from "@mui/icons-material/Search";
import GuideShell from "@/components/guide/GuideShell";
import {
  GUIDE_AUDIENCE_LABELS,
  GUIDE_SECTIONS,
  GuideAudience,
} from "@/lib/guideContent";

const FILTERS: GuideAudience[] = [
  "all",
  "admin",
  "finance",
  "hr",
  "payroll",
  "operations",
  "ess",
  "integrations",
  "platform",
];

export default function UserGuidePage() {
  const [activeId, setActiveId] = useState(GUIDE_SECTIONS[0].id);
  const [query, setQuery] = useState("");
  const [audience, setAudience] = useState<GuideAudience>("all");

  useEffect(() => {
    const applyHash = () => {
      const id = window.location.hash.replace(/^#/, "");
      if (id && GUIDE_SECTIONS.some((s) => s.id === id)) {
        setActiveId(id);
        setTimeout(() => {
          document.getElementById(`guide-${id}`)?.scrollIntoView({ block: "start" });
        }, 80);
      }
    };
    applyHash();
    window.addEventListener("hashchange", applyHash);
    return () => window.removeEventListener("hashchange", applyHash);
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return GUIDE_SECTIONS.filter((s) => {
      if (audience !== "all" && !s.audience.includes(audience) && !s.audience.includes("all")) {
        return false;
      }
      if (!q) return true;
      const blob = [
        s.title,
        s.summary,
        ...(s.tips || []),
        ...s.steps.flatMap((st) => [st.title, st.detail]),
      ]
        .join(" ")
        .toLowerCase();
      return blob.includes(q);
    });
  }, [query, audience]);

  const goSection = (id: string) => {
    setActiveId(id);
    window.history.replaceState(null, "", `#${id}`);
    document.getElementById(`guide-${id}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const sidebar = (
    <Box sx={{ p: 2 }}>
      <Typography
        variant="overline"
        color="text.secondary"
        sx={{ letterSpacing: "0.12em", display: "block", mb: 1 }}
      >
        Contents
      </Typography>
      <TextField
        size="small"
        fullWidth
        placeholder="Search…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        sx={{ mb: 1.5 }}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon fontSize="small" />
            </InputAdornment>
          ),
        }}
      />
      <Stack direction="row" flexWrap="wrap" gap={0.5} sx={{ mb: 1.5 }}>
        {FILTERS.map((f) => (
          <Chip
            key={f}
            size="small"
            label={GUIDE_AUDIENCE_LABELS[f]}
            color={audience === f ? "primary" : "default"}
            variant={audience === f ? "filled" : "outlined"}
            onClick={() => setAudience(f)}
          />
        ))}
      </Stack>
      <List dense disablePadding>
        {filtered.map((s) => (
          <ListItemButton
            key={s.id}
            selected={s.id === activeId}
            onClick={() => goSection(s.id)}
            sx={{
              borderRadius: 1,
              mb: 0.25,
              borderLeft: "3px solid",
              borderColor: s.id === activeId ? "primary.main" : "transparent",
            }}
          >
            <ListItemText
              primary={s.title.replace(/^\d+\.\s*/, "")}
              primaryTypographyProps={{
                variant: "body2",
                fontWeight: s.id === activeId ? 700 : 500,
                fontSize: "0.82rem",
              }}
            />
          </ListItemButton>
        ))}
        {filtered.length === 0 ? (
          <Typography variant="body2" color="text.secondary" sx={{ px: 1, py: 2 }}>
            No chapters match.
          </Typography>
        ) : null}
      </List>
    </Box>
  );

  return (
    <GuideShell sidebar={sidebar} onPrint={() => window.print()}>
      <GlobalStyles
        styles={{
          "@media print": {
            ".noprint": { display: "none !important" },
            ".sierp-guide-shell": { background: "#fff !important" },
            ".guide-chapter": {
              breakInside: "avoid",
              boxShadow: "none !important",
              border: "1px solid #ccc !important",
            },
          },
        }}
      />

      <Box sx={{ mb: 3 }} className="noprint">
        <Typography
          sx={{
            fontFamily: '"Fraunces", Georgia, serif',
            fontWeight: 700,
            fontSize: { xs: "1.75rem", md: "2.1rem" },
            letterSpacing: "-0.03em",
            lineHeight: 1.15,
            mb: 1,
          }}
        >
          How to run SI-ERP
        </Typography>
        <Typography color="text.secondary" sx={{ maxWidth: 560, mb: 1.5 }}>
          Step-by-step playbook for every SI-ERP app: finance, sales, inventory, documents,
          workflows, HR, payroll, Employee Self-Service, and integrations.
        </Typography>
        <Chip label={`${filtered.length} chapters`} color="primary" size="small" />
      </Box>

      <Stack spacing={2.5}>
        {filtered.map((section) => (
          <Paper
            key={section.id}
            id={`guide-${section.id}`}
            className="guide-chapter"
            elevation={0}
            sx={{
              p: { xs: 2, md: 3 },
              scrollMarginTop: 88,
              borderRadius: 2.5,
              border: "1px solid",
              borderColor: "divider",
              bgcolor: (t) =>
                t.palette.mode === "dark" ? "rgba(255,255,255,0.03)" : "rgba(255,255,255,0.78)",
              backdropFilter: "blur(8px)",
            }}
          >
            <Stack direction="row" flexWrap="wrap" gap={0.5} sx={{ mb: 1.25 }} className="noprint">
              {section.audience
                .filter((a) => a !== "all")
                .map((a) => (
                  <Chip key={a} size="small" label={GUIDE_AUDIENCE_LABELS[a]} variant="outlined" />
                ))}
            </Stack>
            <Typography
              component="h2"
              sx={{
                fontFamily: '"Fraunces", Georgia, serif',
                fontWeight: 700,
                fontSize: "1.35rem",
                letterSpacing: "-0.02em",
                mb: 0.75,
              }}
            >
              {section.title}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {section.summary}
            </Typography>

            <Stepper orientation="vertical" nonLinear activeStep={-1}>
              {section.steps.map((step, idx) => (
                <Step key={step.title} active expanded>
                  <StepLabel>
                    <Typography fontWeight={600}>
                      Step {idx + 1}: {step.title}
                    </Typography>
                  </StepLabel>
                  <StepContent>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      {step.detail}
                    </Typography>
                    {step.href ? (
                      <Button
                        size="small"
                        component={Link}
                        href={step.href}
                        endIcon={<OpenInNewIcon fontSize="small" />}
                        sx={{ mb: 1, textTransform: "none" }}
                        className="noprint"
                      >
                        Open screen
                      </Button>
                    ) : null}
                  </StepContent>
                </Step>
              ))}
            </Stepper>

            {section.tips?.length ? (
              <>
                <Divider sx={{ my: 2 }} />
                <Typography variant="subtitle2" gutterBottom>
                  Tips
                </Typography>
                <Stack component="ul" sx={{ m: 0, pl: 2.5 }}>
                  {section.tips.map((tip) => (
                    <Typography key={tip} component="li" variant="body2" color="text.secondary">
                      {tip}
                    </Typography>
                  ))}
                </Stack>
              </>
            ) : null}
          </Paper>
        ))}
      </Stack>
    </GuideShell>
  );
}
