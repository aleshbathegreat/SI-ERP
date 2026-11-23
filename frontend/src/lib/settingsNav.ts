export type SettingsTab = {
  href: string;
  label: string;
  module: string;
};

export type SettingsGroup = {
  id: string;
  label: string;
  tabs: SettingsTab[];
};

export const SETTINGS_GROUPS: SettingsGroup[] = [
  {
    id: "access",
    label: "Access",
    tabs: [
      { href: "/settings/roles", label: "Roles & SoD", module: "settings.roles" },
      { href: "/settings/users", label: "Users", module: "settings.users" },
      { href: "/settings/security", label: "MFA / Security", module: "dashboard" },
      { href: "/settings/audit", label: "Audit logs", module: "settings.audit" },
    ],
  },
  {
    id: "email",
    label: "Email",
    tabs: [
      { href: "/settings/email", label: "SMTP & mailboxes", module: "settings.email" },
      { href: "/settings/mailbox", label: "Mailbox", module: "settings.email" },
      { href: "/settings/email-templates", label: "Templates", module: "settings.email" },
    ],
  },
  {
    id: "integrations",
    label: "Integrations",
    tabs: [
      { href: "/settings/integrations", label: "Connectors", module: "settings.integrations" },
    ],
  },
  {
    id: "company",
    label: "Company",
    tabs: [
      { href: "/settings/domain", label: "Domain & branding", module: "settings.domain" },
      { href: "/settings/pay-gateway", label: "PayFast", module: "billing" },
      { href: "/settings/ops", label: "Operations", module: "settings.roles" },
      { href: "/settings/doc-series", label: "Doc numbers", module: "settings.doc_series" },
      { href: "/settings/approval-matrix", label: "Approvals", module: "settings.approval_matrix" },
      { href: "/settings/import-hub", label: "Import", module: "settings.import_hub" },
    ],
  },
];

export function tabMatches(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function settingsGroupFor(pathname: string) {
  return SETTINGS_GROUPS.find((group) => group.tabs.some((tab) => tabMatches(pathname, tab.href)));
}
