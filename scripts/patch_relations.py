from pathlib import Path
import re

p = Path("frontend/src/lib/entityCrudDefs.ts")
t = p.read_text(encoding="utf-8")

if "RELATIONS" not in t.split("export const ENTITY_CRUD")[0]:
    t = t.replace(
        'import type { FieldDef } from "@/components/crud/EntityFormFields";\nimport { CURRENCY_OPTIONS } from "@/lib/currencies";',
        'import type { FieldDef } from "@/components/crud/EntityFormFields";\nimport { RELATIONS } from "@/components/crud/RelationSelect";\nimport { CURRENCY_OPTIONS } from "@/lib/currencies";',
    )
    print("import ok")

subs = [
    (
        '{ name: "customer",\n        label: "Customer ID",\n        type: "number",\n        required: true,\n        helperText: "Use the form page dropdown (preferred)",\n      }',
        '{ name: "customer",\n        label: "Customer",\n        type: "relation",\n        required: true,\n        relation: RELATIONS.customer,\n      }',
    ),
    (
        '{ name: "vendor", label: "Vendor ID", type: "number", required: true },',
        '{ name: "vendor", label: "Vendor", type: "relation", required: true, relation: RELATIONS.vendor },',
    ),
    (
        '{ name: "item", label: "Item ID", type: "number", required: true },',
        '{ name: "item", label: "Item", type: "relation", required: true, relation: RELATIONS.item },',
    ),
    (
        '{ name: "bank_account", label: "Bank account", type: "number", required: true },',
        '{ name: "bank_account", label: "Bank account", type: "relation", required: true, relation: RELATIONS.bankAccount },',
    ),
    (
        '{ name: "employee", label: "Employee ID", type: "number", required: true },',
        '{ name: "employee", label: "Employee", type: "relation", required: true, relation: RELATIONS.employee },',
    ),
]

for a, b in subs:
    c = t.count(a)
    if c:
        t = t.replace(a, b)
        print(f"replaced {c}x")
    else:
        print("miss", a[:60].replace("\n", " "))

t2, n = re.subn(
    r'\{\s*name:\s*"assigned_employee",\s*label:\s*"Assigned employee ID",\s*type:\s*"number",',
    '{ name: "assigned_employee", label: "Assigned employee", type: "relation", relation: RELATIONS.employee,',
    t,
    count=1,
)
if n:
    t = t2
    print("assigned_employee ok")
else:
    print("assigned_employee miss")

p.write_text(t, encoding="utf-8")
print("done")
