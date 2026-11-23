"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  ReactNode,
} from "react";
import api from "@/lib/api";
import {
  applyDocumentBranding,
  DEFAULT_BRANDING,
  TenantBranding,
} from "@/lib/branding";
import { useAppSelector } from "@/store/hooks";
import { useBrandTheme } from "@/theme/ColorModeContext";

type BrandingContextValue = {
  branding: TenantBranding;
  refresh: () => Promise<void>;
  setBranding: (b: TenantBranding) => void;
};

const BrandingContext = createContext<BrandingContextValue>({
  branding: DEFAULT_BRANDING,
  refresh: async () => undefined,
  setBranding: () => undefined,
});

function fromOrg(org: {
  name?: string;
  code?: string;
  brand_name?: string;
  brand_tagline?: string;
  brand_primary_color?: string;
  brand_secondary_color?: string;
  brand_logo_url?: string | null;
  brand_logo_dark_url?: string | null;
  brand_favicon_url?: string | null;
} | null): TenantBranding | null {
  if (!org) return null;
  return {
    mode: "tenant",
    name: org.name,
    code: org.code,
    brand_name: org.brand_name || org.name || DEFAULT_BRANDING.brand_name,
    brand_tagline: org.brand_tagline || DEFAULT_BRANDING.brand_tagline,
    brand_primary_color: org.brand_primary_color || DEFAULT_BRANDING.brand_primary_color,
    brand_secondary_color:
      org.brand_secondary_color || DEFAULT_BRANDING.brand_secondary_color,
    brand_logo_url: org.brand_logo_url || null,
    brand_logo_dark_url: org.brand_logo_dark_url || org.brand_logo_url || null,
    brand_favicon_url: org.brand_favicon_url || null,
  };
}

export function BrandingProvider({ children }: { children: ReactNode }) {
  const organization = useAppSelector((s) => s.auth.organization);
  const [branding, setBrandingState] = useState<TenantBranding>(DEFAULT_BRANDING);
  const { setBrandColors } = useBrandTheme();

  const apply = useCallback(
    (next: TenantBranding) => {
      setBrandingState(next);
      setBrandColors({
        primary: next.brand_primary_color || DEFAULT_BRANDING.brand_primary_color!,
        secondary: next.brand_secondary_color || DEFAULT_BRANDING.brand_secondary_color!,
      });
      applyDocumentBranding(next);
      try {
        localStorage.setItem("tenant_branding", JSON.stringify(next));
      } catch {
        /* ignore */
      }
    },
    [setBrandColors]
  );

  const refresh = useCallback(async () => {
    try {
      const { data } = await api.get<TenantBranding>("/public/resolve-host/");
      const orgBrand = fromOrg(organization);
      // Prefer authenticated org assets when logged in; host branding for public pages
      if (organization && orgBrand?.brand_logo_url) {
        apply({ ...data, ...orgBrand });
      } else if (organization && orgBrand) {
        apply({
          ...data,
          ...orgBrand,
          brand_logo_url: orgBrand.brand_logo_url || data.brand_logo_url,
          brand_logo_dark_url: orgBrand.brand_logo_dark_url || data.brand_logo_dark_url,
          brand_favicon_url: orgBrand.brand_favicon_url || data.brand_favicon_url,
        });
      } else {
        apply({ ...DEFAULT_BRANDING, ...data });
      }
    } catch {
      const orgBrand = fromOrg(organization);
      if (orgBrand) apply(orgBrand);
    }
  }, [apply, organization]);

  useEffect(() => {
    try {
      const raw = localStorage.getItem("tenant_branding");
      if (raw) {
        const cached = JSON.parse(raw) as TenantBranding;
        apply({ ...DEFAULT_BRANDING, ...cached });
      }
    } catch {
      /* ignore */
    }
    refresh();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const orgBrand = fromOrg(organization);
    if (orgBrand) {
      apply({ ...branding, ...orgBrand });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    organization?.id,
    organization?.brand_name,
    organization?.brand_primary_color,
    organization?.brand_logo_url,
    organization?.brand_favicon_url,
    organization?.brand_tagline,
  ]);

  const value = useMemo(
    () => ({
      branding,
      refresh,
      setBranding: apply,
    }),
    [branding, refresh, apply]
  );

  return <BrandingContext.Provider value={value}>{children}</BrandingContext.Provider>;
}

export function useBranding() {
  return useContext(BrandingContext);
}
