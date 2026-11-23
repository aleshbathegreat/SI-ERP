"use client";

import { useMemo, useState, type ReactNode } from "react";
import Link from "next/link";
import { Button, Stack } from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import FormPageShell from "@/components/crud/FormPageShell";
import DetailPageShell, { DetailSection } from "@/components/crud/DetailPageShell";
import EntityDetailView from "@/components/crud/EntityDetailView";
import EntityFormFields, {
  type FieldDef,
} from "@/components/crud/EntityFormFields";
import ModuleGate from "@/components/ModuleGate";
import { useEntityForm, type FormMode } from "@/hooks/useEntityForm";
import { usePermissions } from "@/hooks/usePermissions";
import { applyCreateDefaults } from "@/lib/autoFields";
import { createResource } from "@/lib/crudApi";
import { useSnackbar } from "notistack";
import { errorSnackbarOpts, getApiErrorMessage } from "@/lib/apiError";

type EntityFormDef = {
  moduleKey: string;
  apiPath: string;
  entityLabel: string;
  route: string;
  fields: FieldDef[];
  empty: Record<string, unknown>;
  formSubtitle?: string;
};

type Props = {
  /** Pages may pass the entity definition instead of the individual props. */
  def?: EntityFormDef;
  moduleKey?: string;
  resourcePath?: string;
  entityLabel?: string;
  basePath?: string;
  mode: FormMode;
  id?: string;
  fields?: FieldDef[];
  empty?: Record<string, unknown>;
  titles?: { create?: string; edit?: string; view?: string };
  mapLoaded?: (row: Record<string, unknown>) => Record<string, unknown>;
  mapPayload?: (form: Record<string, unknown>) => unknown;
  /** Optional view title field (e.g. name, code, po_no). */
  viewTitleField?: string;
  viewSections?: { title: string; description?: string; fields: string[] }[];
  /** Extra header buttons on the detail view (e.g. workflow actions). */
  viewActions?: (ctx: {
    form: Record<string, unknown>;
    reload: () => void;
  }) => ReactNode;
  /** Extra content below the detail fields on the view page. */
  viewExtra?: (ctx: {
    form: Record<string, unknown>;
    reload: () => void;
  }) => ReactNode;
  /** Extra content under the fields while creating or editing. */
  belowFields?: (ctx: {
    form: Record<string, unknown>;
    setForm: (updater: (prev: Record<string, unknown>) => Record<string, unknown>) => void;
  }) => ReactNode;
  subtitle?: string;
};

export default function EntityFormRoute({
  def,
  moduleKey = def?.moduleKey || "",
  resourcePath = def?.apiPath || "",
  entityLabel = def?.entityLabel || "",
  basePath = def?.route ? `/${def.route}` : "",
  mode,
  id,
  fields = def?.fields || [],
  empty = def?.empty || {},
  titles,
  mapLoaded,
  mapPayload,
  viewTitleField,
  viewSections,
  viewActions,
  viewExtra,
  belowFields,
  subtitle = def?.formSubtitle,
}: Props) {
  const { canChange } = usePermissions();
  const { enqueueSnackbar } = useSnackbar();
  const [savingNew, setSavingNew] = useState(false);
  const finance = basePath.startsWith("/finance");
  const seededEmpty = useMemo(
    () => (mode === "create" ? applyCreateDefaults(empty, fields) : empty),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [mode]
  );
  const formFields = useMemo(
    () =>
      mode === "view" ? fields : fields.filter((f) => !f.formHidden),
    [fields, mode]
  );
  const toPayload = (f: Record<string, unknown>) => {
    if (mapPayload) return mapPayload(f);
    const out: Record<string, unknown> = { ...f };
    for (const field of fields) {
      if ((field.type === "date" || field.type === "datetime") && out[field.name] === "") {
        out[field.name] = null;
      }
      if (field.type === "number" && (out[field.name] === "" || out[field.name] === undefined)) {
        out[field.name] = null;
      }
      if (
        (field.type === "relation" || field.relation) &&
        (out[field.name] === "" || out[field.name] === 0)
      ) {
        out[field.name] = null;
      }
    }
    for (const field of fields) {
      if (field.formHidden) delete out[field.name];
    }
    delete out.id;
    return out;
  };

  const { form, setForm, loading, saving, save, readOnly, reload } = useEntityForm({
    resourcePath,
    entityLabel,
    basePath,
    mode,
    id,
    empty: seededEmpty,
    mapLoaded,
    fields: formFields,
    mapPayload: toPayload,
  });

  const saveAndNew = async () => {
    if (mode !== "create" || savingNew) return;
    setSavingNew(true);
    try {
      await createResource(resourcePath, toPayload(form));
      enqueueSnackbar("Saved. Ready for the next one.", { variant: "success" });
      setForm(() => ({ ...seededEmpty }));
    } catch (e: unknown) {
      enqueueSnackbar(getApiErrorMessage(e, `Could not save ${entityLabel}`), errorSnackbarOpts);
    } finally {
      setSavingNew(false);
    }
  };

  const editActions =
    mode === "view" ? (
      <>
        {viewActions && !loading ? viewActions({ form, reload }) : null}
        {canChange(moduleKey) && id ? (
          <Button
            component={Link}
            href={`${basePath}/${id}/edit`}
            variant="contained"
            startIcon={<EditIcon />}
          >
            Edit
          </Button>
        ) : null}
      </>
    ) : null;

  if (mode === "view") {
    const titleKey =
      viewTitleField ||
      fields.find((f) =>
        ["name", "code", "po_no", "order_no", "invoice_no", "asset_code", "sku", "loan_number"].includes(
          f.name
        )
      )?.name;
    const headline =
      (titleKey && form[titleKey] != null && String(form[titleKey])) ||
      titles?.view ||
      `${entityLabel} details`;
    const status = form.status != null ? String(form.status) : null;

    return (
      <ModuleGate module={moduleKey}>
        <DetailPageShell
          eyebrow={entityLabel}
          title={String(headline)}
          backHref={basePath}
          status={status}
          loading={loading}
          extraActions={editActions}
        >
          <EntityDetailView fields={fields} values={form} sections={viewSections} />
          {viewExtra ? viewExtra({ form, reload }) : null}
        </DetailPageShell>
      </ModuleGate>
    );
  }

  const title =
    mode === "create"
      ? titles?.create || `New ${entityLabel}`
      : titles?.edit || `Edit ${entityLabel}`;

  return (
    <ModuleGate module={moduleKey}>
      <FormPageShell
        title={title}
        subtitle={subtitle}
        backHref={basePath}
        mode={mode}
        loading={loading}
        saving={saving || savingNew}
        onSubmit={save}
        submitLabel={finance ? "Save and close" : mode === "create" ? "Save" : "Save changes"}
        extraActions={
          finance && mode === "create" ? (
            <Button size="small" variant="outlined" disabled={saving || savingNew} onClick={saveAndNew}>
              Save and new
            </Button>
          ) : null
        }
      >
        {formFields.length > 8 ? (
          <Stack spacing={2}>
            <DetailSection title={finance ? "Main details" : "Primary fields"} defaultExpanded>
              <Stack spacing={2}>
                <EntityFormFields
                  fields={formFields.slice(0, Math.ceil(formFields.length / 2))}
                  values={form}
                  readOnly={readOnly}
                  mode={mode}
                  onChange={(name, value) =>
                    setForm((prev) => ({ ...prev, [name]: value }))
                  }
                />
              </Stack>
            </DetailSection>
            <DetailSection title={finance ? "More details" : "Additional fields"} defaultExpanded={finance}>
              <Stack spacing={2}>
                <EntityFormFields
                  fields={formFields.slice(Math.ceil(formFields.length / 2))}
                  values={form}
                  readOnly={readOnly}
                  mode={mode}
                  onChange={(name, value) =>
                    setForm((prev) => ({ ...prev, [name]: value }))
                  }
                />
              </Stack>
            </DetailSection>
          </Stack>
        ) : (
          <EntityFormFields
            fields={formFields}
            values={form}
            readOnly={readOnly}
            mode={mode}
            onChange={(name, value) =>
              setForm((prev) => ({ ...prev, [name]: value }))
            }
          />
        )}
        {belowFields ? belowFields({ form, setForm }) : null}
      </FormPageShell>
    </ModuleGate>
  );
}
