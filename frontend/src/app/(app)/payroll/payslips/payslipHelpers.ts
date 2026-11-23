export const moneyFields = [
  "basic",
  "housing_allowance",
  "transport_allowance",
  "medical_allowance",
  "meal_allowance",
  "overtime",
  "bonus",
  "commission",
  "other_earnings",
  "income_tax",
  "eobi",
  "provident_fund",
  "pension",
  "loan_repayment",
  "advance_recovery",
  "other_deductions",
  "employer_provident_fund",
] as const;

export type MoneyKey = (typeof moneyFields)[number];

export const FIELD_LABELS: Record<string, string> = {
  basic: "Basic salary",
  housing_allowance: "Housing allowance",
  transport_allowance: "Transport allowance",
  medical_allowance: "Medical allowance",
  meal_allowance: "Meal / food allowance",
  overtime: "Overtime pay",
  bonus: "Bonus",
  commission: "Commission",
  other_earnings: "Other earnings",
  income_tax: "Income tax / PAYE",
  eobi: "Social security / EOBI",
  provident_fund: "Provident fund (employee)",
  pension: "Pension contribution",
  loan_repayment: "Loan / EMI repayment",
  advance_recovery: "Advance recovery",
  other_deductions: "Other deductions",
  employer_provident_fund: "Employer PF (cost)",
  days_worked: "Days worked",
  unpaid_leave_days: "Unpaid leave days",
  overtime_hours: "Overtime hours",
};

export const slipEmpty: Record<string, string> = {
  period: "",
  employee: "",
  currency: "PKR",
  basic: "0",
  housing_allowance: "0",
  transport_allowance: "0",
  medical_allowance: "0",
  meal_allowance: "0",
  overtime: "0",
  bonus: "0",
  commission: "0",
  other_earnings: "0",
  income_tax: "0",
  eobi: "0",
  provident_fund: "0",
  pension: "0",
  loan_repayment: "0",
  advance_recovery: "0",
  other_deductions: "0",
  employer_provident_fund: "0",
  days_worked: "30",
  unpaid_leave_days: "0",
  overtime_hours: "0",
  payment_method: "bank_transfer",
  bank_account: "",
  payment_reference: "",
  payment_date: "",
  remarks: "",
  net_pay: "0",
  gross_pay: "0",
};

function n(v: string | number | undefined) {
  return Number(v ?? 0) || 0;
}

export function recomputeNet(form: Record<string, string>) {
  const earn =
    n(form.basic) +
    n(form.housing_allowance) +
    n(form.transport_allowance) +
    n(form.medical_allowance) +
    n(form.meal_allowance) +
    n(form.overtime) +
    n(form.bonus) +
    n(form.commission) +
    n(form.other_earnings);
  const ded =
    n(form.income_tax) +
    n(form.eobi) +
    n(form.provident_fund) +
    n(form.pension) +
    n(form.loan_repayment) +
    n(form.advance_recovery) +
    n(form.other_deductions);
  return {
    ...form,
    gross_pay: earn.toFixed(2),
    net_pay: (earn - ded).toFixed(2),
  };
}
