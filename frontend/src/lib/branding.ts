export type TenantBranding = {
  mode?: string;
  name?: string;
  code?: string | null;
  brand_name: string;
  brand_tagline?: string;
  brand_primary_color?: string;
  brand_secondary_color?: string;
  brand_logo_url?: string | null;
  brand_logo_dark_url?: string | null;
  brand_favicon_url?: string | null;
};

/** Platform (SI-ERP) identity — SI Global / SIGBL */
export const PLATFORM_LOGO_URL =
  "https://sigbl.com/wp-content/uploads/2024/04/cropped-sigbl_logo_cv-1.png";

export const DEFAULT_BRANDING: TenantBranding = {
  mode: "platform",
  name: "SI-ERP",
  brand_name: "SI-ERP",
  brand_tagline: "A-Symmetric ICT Solutions · Finance, HR & Payroll",
  brand_primary_color: "#00A3C4",
  brand_secondary_color: "#0B3D5C",
  brand_logo_url: PLATFORM_LOGO_URL,
  brand_logo_dark_url: PLATFORM_LOGO_URL,
  brand_favicon_url: PLATFORM_LOGO_URL,
};

export function logoForMode(branding: TenantBranding, dark: boolean): string | null {
  if (dark) {
    return branding.brand_logo_dark_url || branding.brand_logo_url || null;
  }
  return branding.brand_logo_url || branding.brand_logo_dark_url || null;
}

export function applyDocumentBranding(branding: TenantBranding) {
  if (typeof document === "undefined") return;
  const path = window.location.pathname;
  const keepPageTitle = path === "/" || path === "/pricing" || path.startsWith("/legal");
  if (!keepPageTitle) {
    document.title = branding.brand_name || DEFAULT_BRANDING.brand_name;
  }
  const href =
    branding.brand_favicon_url || branding.brand_logo_url || PLATFORM_LOGO_URL;
  let link = document.querySelector<HTMLLinkElement>("link[rel='icon']");
  if (!link) {
    link = document.createElement("link");
    link.rel = "icon";
    document.head.appendChild(link);
  }
  link.href = href;
}
