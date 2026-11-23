"use client";

import type { ReactNode } from "react";
import type { FieldDef } from "@/components/crud/EntityFormFields";
import {
  DetailGrid,
  DetailItem,
  DetailSection,
} from "@/components/crud/DetailPageShell";
import StatusChip from "@/components/crud/StatusChip";
import { formatDate, formatDateTime } from "@/lib/format";

function displayValue(field: FieldDef, raw: unknown): ReactNode {
  if (raw === null || raw === undefined || raw === "") return "—";

  if (field.type === "boolean") {
    const yes = raw === true || raw === "yes" || raw === "true";
    return yes ? "Yes" : "No";
  }

  if (field.type === "date") {
    return formatDate(String(raw));
  }

  if (field.type === "datetime") {
    return formatDateTime(String(raw));
  }

  if (field.name === "status" || field.name.endsWith("_status")) {
    return <StatusChip status={String(raw)} />;
  }

  if (field.type === "select" && field.options?.length) {
    const opt = field.options.find((o) => o.value === String(raw));
    return opt?.label || String(raw);
  }

  if (field.type === "number") {
    const n = Number(raw);
    if (!Number.isNaN(n)) {
      return n.toLocaleString(undefined, { maximumFractionDigits: 4 });
    }
  }

  return String(raw);
}

/** Split fields into Overview (first half / identity) and Details. */
function splitSections(fields: FieldDef[]) {
  if (fields.length <= 6) {
    return [{ title: "Details", fields }];
  }
  const mid = Math.ceil(fields.length / 2);
  return [
    { title: "Overview", fields: fields.slice(0, mid) },
    { title: "Additional details", fields: fields.slice(mid) },
  ];
}

export default function EntityDetailView({
  fields,
  values,
  sections,
}: {
  fields: FieldDef[];
  values: Record<string, unknown>;
  /** Optional explicit sections; otherwise auto-split. */
  sections?: { title: string; description?: string; fields: string[] }[];
}) {
  const resolved = sections
    ? sections.map((s) => ({
        title: s.title,
        description: s.description,
        fields: s.fields
          .map((name) => fields.find((f) => f.name === name))
          .filter(Boolean) as FieldDef[],
      }))
    : splitSections(fields);

  return (
    <>
      {resolved.map((sec, idx) =>
        sec.fields.length ? (
          <DetailSection
            key={sec.title}
            title={sec.title}
            description={sec.description}
            defaultExpanded={idx === 0}
          >
            <DetailGrid>
              {sec.fields.map((f) => (
                <DetailItem
                  key={f.name}
                  label={f.label}
                  value={displayValue(f, values[f.name])}
                  fullWidth={f.type === "textarea"}
                />
              ))}
            </DetailGrid>
          </DetailSection>
        ) : null
      )}
    </>
  );
}
