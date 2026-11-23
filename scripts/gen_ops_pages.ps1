$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$routes = @(
  "sales/customers",
  "sales/orders",
  "inventory/items",
  "inventory/movements",
  "procurement/orders",
  "settings/email-templates"
)

function Write-Utf8NoBom($path, $content) {
  $dir = Split-Path $path -Parent
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
  [IO.File]::WriteAllText($path, $content)
}

$listTpl = @'
"use client";

import EntityListRoute from "@/components/crud/EntityListRoute";
import { getEntityDef } from "@/lib/entityCrudDefs";

const def = getEntityDef("__ROUTE__")!;

export default function Page() {
  return <EntityListRoute def={def} />;
}
'@

$newTpl = @'
"use client";

import EntityFormRoute from "@/components/crud/EntityFormRoute";
import { getEntityDef } from "@/lib/entityCrudDefs";

const def = getEntityDef("__ROUTE__")!;

export default function Page() {
  return (
    <EntityFormRoute
      moduleKey={def.moduleKey}
      resourcePath={def.apiPath}
      entityLabel={def.entityLabel}
      basePath={`/${def.route}`}
      mode="create"
      fields={def.fields}
      empty={def.empty}
    />
  );
}
'@

$viewTpl = @'
"use client";

import { useParams } from "next/navigation";
import EntityFormRoute from "@/components/crud/EntityFormRoute";
import { getEntityDef } from "@/lib/entityCrudDefs";

const def = getEntityDef("__ROUTE__")!;

export default function Page() {
  const params = useParams();
  return (
    <EntityFormRoute
      moduleKey={def.moduleKey}
      resourcePath={def.apiPath}
      entityLabel={def.entityLabel}
      basePath={`/${def.route}`}
      mode="view"
      id={String(params.id)}
      fields={def.fields}
      empty={def.empty}
    />
  );
}
'@

$editTpl = @'
"use client";

import { useParams } from "next/navigation";
import EntityFormRoute from "@/components/crud/EntityFormRoute";
import { getEntityDef } from "@/lib/entityCrudDefs";

const def = getEntityDef("__ROUTE__")!;

export default function Page() {
  const params = useParams();
  return (
    <EntityFormRoute
      moduleKey={def.moduleKey}
      resourcePath={def.apiPath}
      entityLabel={def.entityLabel}
      basePath={`/${def.route}`}
      mode="edit"
      id={String(params.id)}
      fields={def.fields}
      empty={def.empty}
    />
  );
}
'@

foreach ($route in $routes) {
  $base = Join-Path $root "frontend\src\app\(app)\$($route.Replace('/','\'))"
  Write-Utf8NoBom (Join-Path $base "page.tsx") ($listTpl.Replace("__ROUTE__", $route))
  Write-Utf8NoBom (Join-Path $base "new\page.tsx") ($newTpl.Replace("__ROUTE__", $route))
  Write-Utf8NoBom (Join-Path $base "[id]\page.tsx") ($viewTpl.Replace("__ROUTE__", $route))
  Write-Utf8NoBom (Join-Path $base "[id]\edit\page.tsx") ($editTpl.Replace("__ROUTE__", $route))
  Write-Host "pages=$route"
}
Write-Host DONE
