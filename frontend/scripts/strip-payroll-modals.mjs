import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const p = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  "../src/app/(app)/payroll/page.tsx"
);
let s = fs.readFileSync(p, "utf8");

s = s.split('import FormDialog from "@/components/crud/FormDialog";\n').join("");
s = s.split('import FormDialog from "@/components/crud/FormDialog";\r\n').join("");
s = s.split(
  'import { useCrudController } from "@/hooks/useCrudController";'
).join('import { useCrudList } from "@/hooks/useCrudList";');

s = s.replace(
  `const periods = useCrudController<Period>("/payroll/periods/", "Payroll period");
  const slips = useCrudController<Payslip>("/payroll/payslips/", "Payslip");
  const [pForm, setPForm] = useState(periodEmpty);
  const [sForm, setSForm] = useState(slipEmpty);`,
  `const periods = useCrudList<Period>("/payroll/periods/", "Payroll period", "/payroll/periods");
  const slips = useCrudList<Payslip>("/payroll/payslips/", "Payslip", "/payroll/payslips");`
);

// Remove period form sync effect
s = s.replace(
  /\n  useEffect\(\(\) => \{\n    if \(periods\.mode === "create"\) \{[\s\S]*?\n  \}, \[periods\.mode, periods\.active\]\);\n/,
  "\n"
);

// Remove slip form sync effect  
s = s.replace(
  /\n  useEffect\(\(\) => \{\n    if \(slips\.mode === "create"\) \{[\s\S]*?\n  \}, \[slips\.mode, slips\.active, periodFilter, periods\.rows\]\);\n/,
  "\n"
);

// Remove helpers only used by modals if unused - keep for now if referenced

// Strip FormDialog blocks (periods then payslips)
s = s.replace(
  /\n\s*<FormDialog[\s\S]*?<\/FormDialog>/g,
  ""
);

// Remove dead constants if present and unused - periodEmpty, slipEmpty, etc.
// Safer: leave them; TypeScript/eslint may warn. Strip large dead blocks:
const deadStarts = [
  "const periodEmpty = {",
  "const moneyFields = [",
  "const slipEmpty: Record<string, string> = {",
  "const FIELD_LABELS: Record<string, string> = {",
  "function n(v: string | number | undefined) {",
  "function recomputeNet(form: Record<string, string>) {",
];

// Only remove if FormDialog gone and pForm gone
if (!s.includes("FormDialog") && !s.includes("pForm") && !s.includes("sForm")) {
  // remove periodEmpty block
  s = s.replace(
    /const periodEmpty = \{[\s\S]*?\};\r?\n\r?\n/,
    ""
  );
  s = s.replace(
    /const moneyFields = \[[\s\S]*?\] as const;\r?\n\r?\ntype MoneyKey = \(typeof moneyFields\)\[number\];\r?\n\r?\n/,
    ""
  );
  s = s.replace(
    /const slipEmpty: Record<string, string> = \{[\s\S]*?\};\r?\n\r?\n/,
    ""
  );
  s = s.replace(
    /const FIELD_LABELS: Record<string, string> = \{[\s\S]*?\};\r?\n\r?\n/,
    ""
  );
  s = s.replace(
    /function n\(v: string \| number \| undefined\) \{[\s\S]*?\}\r?\n\r?\n/,
    ""
  );
  s = s.replace(
    /function recomputeNet\(form: Record<string, string>\) \{[\s\S]*?\}\r?\n\r?\n/,
    ""
  );
}

// Clean unused imports that were only for forms
if (!s.includes("<TextField") && !s.includes("TextField ")) {
  s = s.replace(/\s*TextField,\r?\n/, "\n");
}
if (!s.includes("MenuItem")) {
  s = s.replace(/\s*MenuItem,\r?\n/, "\n");
}
if (!s.includes("Divider")) {
  s = s.replace(/\s*Divider,\r?\n/, "\n");
}

fs.writeFileSync(p, s);
console.log({
  FormDialog: s.includes("FormDialog"),
  useCrudController: s.includes("useCrudController"),
  useCrudList: s.includes("useCrudList"),
  pForm: s.includes("pForm"),
  sForm: s.includes("sForm"),
  periodEmpty: s.includes("periodEmpty"),
});
