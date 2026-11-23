export const WORKFLOW_TARGETS = [
  { value: "dms.documents", label: "Documents" },
  { value: "finance.journals", label: "Journals" },
  { value: "finance.budgets", label: "Budgets" },
  { value: "finance.invoices", label: "Vendor invoices" },
  { value: "sales.invoices", label: "Customer invoices" },
  { value: "sales.orders", label: "Sales orders" },
  { value: "procurement.requisitions", label: "Purchase requisitions" },
  { value: "procurement.orders", label: "Purchase orders" },
  { value: "hr.leaves", label: "Leave requests" },
  { value: "hr.recruitment", label: "Recruitment" },
  { value: "hr.performance", label: "Performance reviews" },
  { value: "payroll.periods", label: "Payroll periods" },
  { value: "payroll.loans", label: "Employee loans" },
  { value: "projects.timesheets", label: "Timesheets" },
];

export const RECORD_HREF: Record<string, string> = {
  "dms.documents": "/dms/documents",
  "finance.journals": "/finance/journals",
  "finance.budgets": "/finance/budgets",
  "finance.invoices": "/finance/invoices",
  "sales.invoices": "/sales/invoices",
  "sales.orders": "/sales/orders",
  "procurement.requisitions": "/procurement/requisitions",
  "procurement.orders": "/procurement/orders",
  "hr.leaves": "/hr/leaves",
  "hr.recruitment": "/hr/recruitment",
  "hr.performance": "/hr/performance",
  "payroll.periods": "/payroll/periods",
  "payroll.loans": "/payroll/loans",
  "projects.timesheets": "/projects/timesheets",
};

export function workflowTargetLabel(value: string) {
  return WORKFLOW_TARGETS.find((row) => row.value === value)?.label || value;
}
