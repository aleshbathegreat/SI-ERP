"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Tab, Tabs } from "@mui/material";
import { usePermissions } from "@/hooks/usePermissions";
import { settingsGroupFor, tabMatches } from "@/lib/settingsNav";

export default function SettingsTabs() {
  const pathname = usePathname();
  const { canView } = usePermissions();
  const group = settingsGroupFor(pathname);
  if (!group) return null;
  const tabs = group.tabs.filter((tab) => canView(tab.module));
  if (tabs.length < 2) return null;
  const current = tabs.find((tab) => tabMatches(pathname, tab.href))?.href ?? false;

  return (
    <Tabs
      value={current}
      variant="scrollable"
      scrollButtons="auto"
      sx={{ mb: 2, borderBottom: 1, borderColor: "divider" }}
    >
      {tabs.map((tab) => (
        <Tab
          key={tab.href}
          label={tab.label}
          value={tab.href}
          component={Link}
          href={tab.href}
        />
      ))}
    </Tabs>
  );
}
