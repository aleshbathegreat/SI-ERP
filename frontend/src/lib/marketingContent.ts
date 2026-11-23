export type ModuleGroup = "Finance" | "Commercial" | "Plant" | "People" | "Control";

export const MODULES: { name: string; text: string; group: ModuleGroup }[] = [
  { group: "Finance", name: "General ledger", text: "Chart of accounts, journals, open periods, and the reports a finance lead closes on." },
  { group: "Finance", name: "Payables", text: "Vendors, bills, payment terms, and withholding detail on the vendor record." },
  { group: "Finance", name: "Receivables", text: "Customers, invoices, credit limits, and the cash you still have to collect." },
  { group: "Finance", name: "Bank and assets", text: "Bank activity, cheques, fixed assets, and depreciation in the same ledger." },
  { group: "Finance", name: "Tax and e-invoice", text: "Tax returns and e-invoices prepared from the documents already in finance." },
  { group: "Finance", name: "Intercompany", text: "Movement between companies in the group, visible as its own register." },
  { group: "Commercial", name: "Sales", text: "Quotes, sales orders, price lists, and the invoice that follows the order." },
  { group: "Commercial", name: "CRM", text: "A pipeline board, a sales calendar, and a quotation from the same deal." },
  { group: "Commercial", name: "Inventory", text: "Items, bins, pick lists, and labels for the warehouse floor." },
  { group: "Commercial", name: "Procurement", text: "Requisitions and purchase orders with the same item master sales uses." },
  { group: "Plant", name: "Manufacturing", text: "Bills of material and work orders for a mill or a discrete plant." },
  { group: "Plant", name: "Quality", text: "Inspections, non-conformance, and corrective action on one quality desk." },
  { group: "Plant", name: "Maintenance", text: "Preventive schedules and maintenance orders against the assets you already track." },
  { group: "Plant", name: "Service", text: "Customer cases and notes after the goods have left the gate." },
  { group: "Plant", name: "Projects", text: "Projects and timesheets for work that is sold by the job." },
  { group: "Commercial", name: "Contracts", text: "Sales contracts held with the customer they belong to." },
  { group: "People", name: "Human resources", text: "People, leave, attendance, recruitment, and performance." },
  { group: "People", name: "Payroll", text: "Pay runs that post into the general ledger." },
  { group: "People", name: "Employee self-service", text: "Leave, attendance, payslips, and profile for the people on the floor." },
  { group: "Control", name: "Documents", text: "Folders, types, tags, versions, checkout, and restricted access." },
  { group: "Control", name: "Microsoft 365", text: "Save a document to OneDrive or SharePoint. Standard save covers files up to 4 MB." },
  { group: "Control", name: "Workflows", text: "States, transitions, triggers, actions, signatures, and a 48-hour escalation path." },
  { group: "Control", name: "Approvals", text: "A queue for the person who must sign, separate from the person who prepared." },
  { group: "Control", name: "Audit trail", text: "A human-readable history of who changed a record and when it was refused." },
  { group: "Control", name: "Inbox, comments, tasks", text: "Notifications, comments, and tasks inside the same company workspace." },
];

export const FITS: { title: string; plan: string; text: string }[] = [
  { title: "A mill or a plant", plan: "Annual", text: "One site, a real close, stock on the floor, and payroll that has to hit the ledger." },
  { title: "A trading house", plan: "Monthly, then Annual", text: "Quotes, orders, credit limits, and the cash still to collect. Prove it for a month, then take the year." },
  { title: "A group with more sites", plan: "Enterprise", text: "More companies, more people on self-service, and a faster reply from SI Global." },
  { title: "A first look", plan: "Trial", text: "Fourteen days on the same apps. No card. Invite finance and the warehouse before you choose a plan." },
];

export const FIRST_DAYS: { day: string; title: string; text: string }[] = [
  { day: "Day 1", title: "Open the company", text: "Name the company, set the owner, and sign in. The trial is the real workspace." },
  { day: "Day 3", title: "Seat the people who close", text: "Invite finance, the warehouse, and one approver. Roles decide who can post and who can only see." },
  { day: "Day 14", title: "Choose the year or stop", text: "If the close and the pay run belong in this ledger, move to Annual or Enterprise. If they do not, the trial ends." },
];

export const PILLARS: { title: string; points: string[] }[] = [
  { title: "Finance", points: ["Journals and periods", "Payables and receivables", "Bank, assets, tax", "E-invoice and reports"] },
  { title: "Commercial", points: ["CRM and quotes", "Sales orders", "Inventory and picking", "Procurement"] },
  { title: "Plant", points: ["Bills of material", "Work orders", "Quality and CAPA", "Maintenance"] },
  { title: "People", points: ["HR records", "Leave and attendance", "Payroll to the ledger", "Employee self-service"] },
  { title: "Control", points: ["Documents and versions", "Workflows and signatures", "Approvals", "Audit trail"] },
];

export const INDUSTRIES = [
  "Manufacturing",
  "Textile mills",
  "Pharma",
  "Food",
  "Trading houses",
  "Construction",
  "Logistics",
  "Multi-site groups",
];

export type PlanCard = {
  code: string;
  name: string;
  price: string;
  interval: string;
  summary: string;
  max_functional_users: number;
  max_ess_users: number;
};

export const FALLBACK_PLANS: PlanCard[] = [
  {
    code: "trial",
    name: "Trial",
    price: "0",
    interval: "trial",
    summary: "14-day full ERP trial. Finance, HR and Payroll included.",
    max_functional_users: 10,
    max_ess_users: 25,
  },
  {
    code: "monthly",
    name: "Monthly",
    price: "7500",
    interval: "month",
    summary: "Billed monthly. Full Finance, HR and Payroll SaaS access.",
    max_functional_users: 10,
    max_ess_users: 50,
  },
  {
    code: "annual",
    name: "Annual",
    price: "75000",
    interval: "year",
    summary: "Billed yearly (2 months included). Full ERP module access.",
    max_functional_users: 25,
    max_ess_users: 200,
  },
  {
    code: "enterprise",
    name: "Enterprise",
    price: "150000",
    interval: "year",
    summary: "Annual enterprise seat pack with priority support.",
    max_functional_users: 100,
    max_ess_users: 1000,
  },
];
