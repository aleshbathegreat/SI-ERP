/**
 * Generates list + /new + /[id] + /[id]/edit pages from ENTITY_CRUD routes.
 * Run: node scripts/gen-entity-routes.mjs
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.join(__dirname, "..", "src", "app", "(app)");

/** Keep in sync with src/lib/entityCrudDefs.ts route keys */
const ROUTES = [
  "hr/departments",
  "hr/designations",
  "hr/leave-types",
  "hr/benefits",
  "hr/recruitment",
  "hr/training",
  "hr/separations",
  "hr/probation",
  "hr/performance",
  "hr/documents",
  "finance/cost-centers",
  "finance/accounts",
  "finance/vendors",
  "finance/banks",
  "finance/tax",
  "finance/assets",
  "finance/reconciliations",
  "finance/budgets",
  "finance/treasury",
  "payroll/structures",
];

function ensureDir(p) {
  fs.mkdirSync(p, { recursive: true });
}

function write(file, contents) {
  ensureDir(path.dirname(file));
  fs.writeFileSync(file, contents, "utf8");
  console.log("wrote", path.relative(path.join(__dirname, ".."), file));
}

for (const route of ROUTES) {
  const dir = path.join(appRoot, ...route.split("/"));
  const listPage = `"use client";

import EntityListRoute from "@/components/crud/EntityListRoute";
import { getEntityDef } from "@/lib/entityCrudDefs";

const def = getEntityDef("${route}")!;

export default function Page() {
  return <EntityListRoute def={def} />;
}
`;

  const formPage = (mode, idExpr) => `"use client";

import EntityFormRoute from "@/components/crud/EntityFormRoute";
import { getEntityDef } from "@/lib/entityCrudDefs";
${mode !== "create" ? 'import { useParams } from "next/navigation";\n' : ""}
const def = getEntityDef("${route}")!;

export default function Page() {
${mode !== "create" ? "  const params = useParams();\n  const id = String(params.id);\n" : ""}  return (
    <EntityFormRoute
      moduleKey={def.moduleKey}
      resourcePath={def.apiPath}
      entityLabel={def.entityLabel}
      basePath={\`/\${def.route}\`}
      mode="${mode}"
${mode !== "create" ? "      id={id}\n" : ""}      fields={def.fields}
      empty={def.empty}
    />
  );
}
`;

  write(path.join(dir, "page.tsx"), listPage);
  write(path.join(dir, "new", "page.tsx"), formPage("create"));
  write(path.join(dir, "[id]", "page.tsx"), formPage("view"));
  write(path.join(dir, "[id]", "edit", "page.tsx"), formPage("edit"));
}

console.log("Done", ROUTES.length, "entities");
