export type GuideAudience =
  | "all"
  | "admin"
  | "finance"
  | "hr"
  | "payroll"
  | "operations"
  | "ess"
  | "integrations"
  | "platform";

export type GuideStep = {
  title: string;
  detail: string;
  href?: string;
};

export type GuideSection = {
  id: string;
  title: string;
  summary: string;
  audience: GuideAudience[];
  steps: GuideStep[];
  tips?: string[];
};

/** In-app user guide — keep here so /guide stays thin and reusable (ESS deep-links, search). */
export const GUIDE_SECTIONS: GuideSection[] = [
  {
    id: "start",
    title: "1. Sign in & find your way",
    summary:
      "Open your organization address, sign in, then use the sidebar and the header (notifications, theme, guide).",
    audience: ["all", "admin", "finance", "hr", "payroll", "operations"],
    steps: [
      {
        title: "Open the login page",
        detail:
          "Use your organization address (for example https://si-erp.mushaz.com). Enter the username and password from your admin. Forgot password emails a reset link from the platform mailbox.",
        href: "/login",
      },
      {
        title: "Land on the dashboard",
        detail:
          "After login you see role-aware KPIs. ESS-only users may land on the Employee portal instead. A sign-in lasts 24 hours.",
        href: "/dashboard",
      },
      {
        title: "Use the sidebar and header",
        detail:
          "The left nav is permission-filtered. One section stays open at a time. The header has the notification bell, theme, User guide, and profile.",
      },
    ],
    tips: [
      "Only modules your role can view appear in the sidebar.",
      "Open this guide anytime from the book icon in the header.",
      "The bell includes workflow, comment, and task notices. Governance also has Notifications, Comments, and Tasks.",
    ],
  },
  {
    id: "users",
    title: "2. Users, roles & seats",
    summary: "Invite functional and ESS users, assign roles, and stay within package seat limits.",
    audience: ["admin"],
    steps: [
      {
        title: "Open Users",
        detail: "Settings → Access, then the Users tab.",
        href: "/settings/users",
      },
      {
        title: "Invite a user",
        detail:
          "Set username, password, email, and roles. Seat caps from the subscription package are enforced.",
      },
      {
        title: "Assign roles (SoD)",
        detail:
          "Keep preparer and approver separate for journals, invoices, leave, payroll, and any workflow that enforces segregation of duties.",
        href: "/settings/roles",
      },
      {
        title: "Link an employee for ESS",
        detail:
          "HR must link the user to an Employee record so /ess works for that person.",
        href: "/hr/employees",
      },
    ],
    tips: ["Configure MFA under Settings → Access, on the MFA / Security tab.", "Amount bands live under Settings → Company, on the Approvals tab."],
  },
  {
    id: "finance-setup",
    title: "3. Finance setup (CoA → banks → budgets → periods)",
    summary:
      "Master data before posting: GL accounts, cost centers, vendors, bank and cash links, budgets, tax codes, and period close.",
    audience: ["finance", "admin"],
    steps: [
      {
        title: "Account types",
        detail:
          "Classic five types seed automatically. Add subtypes and set the statement class (asset, liability, equity, income, expense) for P&L and the balance sheet.",
        href: "/finance/account-types",
      },
      {
        title: "Chart of Accounts",
        detail:
          "Create GL codes with an account type. An optional parent account builds the hierarchy. Keep codes stable for reporting.",
        href: "/finance/accounts",
      },
      {
        title: "Cost centers and vendors",
        detail:
          "Cost centers feed budgets and journal lines. Vendors need an NTN for withholding tax, plus optional category, terms, and credit limit.",
        href: "/finance/vendors",
      },
      {
        title: "Bank accounts",
        detail:
          "Add each bank (title, bank name, IBAN). Set the linked GL cash account so AP payments post to the right cash ledger.",
        href: "/finance/banks",
      },
      {
        title: "Budgets and tax codes",
        detail:
          "Fiscal-year budgets by cost center update when expense journals post. Tax codes hold WHT rates used on AP invoices.",
        href: "/finance/budgets",
      },
      {
        title: "Period close",
        detail:
          "Finance → Period close: add year and month, then Lock. A locked month blocks journal submit, approve, and post.",
        href: "/finance/periods",
      },
    ],
    tips: [
      "The system creates control accounts when needed: 2100 AP, 2150 WHT payable, 1100 Cash, 5700 Depreciation expense, 1590 Accumulated depreciation.",
      "Link every operating bank to a GL cash account before recording AP payments.",
      "Document number prefixes live under Settings → Company, on the Doc numbers tab.",
    ],
  },
  {
    id: "journals",
    title: "4. Journal entries — debits, credits, then approve",
    summary:
      "Enter each account on its own line. Debits and credits must match. Drafts are approved before they post.",
    audience: ["finance"],
    steps: [
      {
        title: "Enter the journal",
        detail:
          "Finance → Journal entries → New journal entry. Set the journal date and leave the journal no. blank if you want one assigned. Put an account, a debit or a credit, and a description on each line. Add lines until debits equal credits, then Save and close.",
        href: "/finance/journals",
      },
      {
        title: "Submit, approve, and post",
        detail:
          "Status moves only through the workflow buttons. A different user should approve when segregation of duties is on. Post checks the balance, the budget, and an open period.",
      },
      {
        title: "Duplicate or reverse",
        detail:
          "Duplicate creates a new draft. Reverse on a posted journal posts the opposite voucher. The original stays posted for audit.",
      },
    ],
    tips: [
      "Filter the list by Draft, Submitted, Approved, or Posted.",
      "A locked accounting period rejects submit, approve, and post.",
      "A workflow named for Journals can replace the default buttons when its transitions are named Submit, Approve, Reject, or Post.",
    ],
  },
  {
    id: "ap",
    title: "5. Accounts payable — bill, withhold, pay",
    summary:
      "Vendor bills with approval, withholding tax from tax codes, net payable, and a payment that posts the AP, bank, and WHT journal.",
    audience: ["finance"],
    steps: [
      {
        title: "Create a vendor bill",
        detail:
          "Enter the vendor invoice number, or leave it blank for AP-YYYY-#####. Due date defaults to 30 days. Pick a WHT tax code. Net payable is gross minus WHT.",
        href: "/finance/invoices",
      },
      {
        title: "Approve the bill",
        detail:
          "Submit, then Approve. Status is locked after submit. Use the workflow buttons.",
      },
      {
        title: "Record payment",
        detail:
          "On an approved bill, Record payment, choose the paying bank, and enter a payment reference. The system posts Dr trade payables, Cr bank (net), Cr WHT payable.",
      },
      {
        title: "WHT challans and ageing",
        detail:
          "Tax challans roll WHT from AP for a YYYY-MM period. Statutory reports include AP ageing.",
        href: "/finance/challans",
      },
    ],
    tips: [
      "The bank must exist, with a GL cash link, before Record payment.",
      "Vendor bills also start from a goods receipt on a purchase order.",
    ],
  },
  {
    id: "bank-assets",
    title: "6. Bank reconciliation and fixed assets",
    summary:
      "Match a bank statement before close. Register assets and post straight-line depreciation to the general ledger.",
    audience: ["finance"],
    steps: [
      {
        title: "Reconcile a bank",
        detail:
          "Create a reconciliation, upload a CSV, tick lines to match, or use Auto-match. Close when the difference is about zero and every line is matched. Close updates the bank balance.",
        href: "/finance/reconciliations",
      },
      {
        title: "Register a fixed asset",
        detail:
          "Code, cost, and annual straight-line rate. Assign an employee, record repairs, and print a QR sticker.",
        href: "/finance/assets",
      },
      {
        title: "Depreciate and dispose",
        detail:
          "Post annual depreciation from the asset, or run a monthly batch under Asset depreciation. Dispose records proceeds and marks the asset disposed.",
        href: "/finance/asset-depreciation",
      },
    ],
    tips: [
      "CSV headers: date or txn_date, description, amount (or debit and credit), reference.",
      "Depreciation posts Dr 5700 and Cr 1590.",
    ],
  },
  {
    id: "finance-more",
    title: "7. Treasury, FX, cheques, intercompany, and tax filing",
    summary:
      "Cash investments, exchange rates, post-dated cheques, related-party journals, FBR e-invoices, and tax returns.",
    audience: ["finance", "admin"],
    steps: [
      {
        title: "Treasury and FX rates",
        detail:
          "Record investments under Treasury. Maintain the currency list under Currencies, then enter exchange rates under FX rates before you post foreign-currency amounts.",
        href: "/finance/treasury",
      },
      {
        title: "Cheques and post-dated cheques",
        detail: "Track issued and post-dated cheques in the cheque register.",
        href: "/finance/cheques",
      },
      {
        title: "Intercompany",
        detail:
          "Add a partner with AR and AP accounts, then post an intercompany transaction to the general ledger from the row menu.",
        href: "/finance/intercompany",
      },
      {
        title: "FBR e-invoice and tax returns",
        detail:
          "An approved customer invoice creates an e-invoice draft. Submit it when FBR is configured. Tax returns build sales tax and WHT from AR, AP, and challans.",
        href: "/finance/e-invoices",
      },
    ],
    tips: [
      "Tax returns are under Finance → Tax returns.",
      "E-invoice submit stays in sandbox until FBR_API_URL is set on the server.",
    ],
  },
  {
    id: "reports",
    title: "8. Statutory finance reports",
    summary:
      "Trial balance, profit and loss, balance sheet, cash, cash flow, AP and AR ageing, stock valuation, WHT register, payroll register, and budget versus actual.",
    audience: ["finance", "admin"],
    steps: [
      {
        title: "Open Statutory reports",
        detail: "Set As of date and Fiscal year, then Apply.",
        href: "/finance/reports",
      },
      {
        title: "Read the statements",
        detail:
          "Confirm the trial balance is balanced before you lock a period. Use AP and AR ageing for collections. Stock valuation, the WHT register, and the payroll register are on the same page.",
      },
      {
        title: "Budget versus actual",
        detail:
          "The tab shows budget, actual posted expense by cost centre, variance, and utilization. Refresh after posting expense journals. Download the current tab as Excel.",
      },
    ],
    tips: ["Amounts display in PKR formatting."],
  },
  {
    id: "crm",
    title: "9. CRM — leads, pipeline, and activities",
    summary: "Qualify a lead on the pipeline board, forecast the month, and log the next call.",
    audience: ["operations", "admin"],
    steps: [
      {
        title: "Capture a lead",
        detail:
          "CRM → Leads. Set the source, campaign, and priority. If the email, phone, or company already exists, SI-ERP shows the matching lead or customer. Convert a qualified lead into a customer and an opportunity.",
        href: "/crm/leads",
      },
      {
        title: "Work the pipeline board",
        detail:
          "Opportunities opens on a board. Drag a deal to the next stage, or use the row menu. Lost asks for a reason and records the date. The strip above is the weighted forecast by month, including deals whose close date has already slipped. Mark won, then create the quotation from the same deal.",
        href: "/crm/opportunities",
      },
      {
        title: "Log the next activity",
        detail:
          "Open the lead or opportunity and schedule a call, meeting, or task. Mark it done from that record or from Activities. An overdue next step shows on the pipeline card.",
        href: "/crm/activities",
      },
      {
        title: "Use the calendar",
        detail:
          "CRM → Calendar shows the month. A start and end time places the meeting in that hour. A due date with no time stays on the day. Switch to Mine for your own book, and download the month as an iCalendar file. Settings → Integrations → Calendars can also copy each meeting to Microsoft 365, Google, and any CalDAV calendar. Turn on one or several. SI-ERP stays the record.",
        href: "/crm/calendar",
      },
      {
        title: "Send and track email",
        detail:
          "Settings → Email opens tabs for SMTP and mailboxes, the mailbox itself, and templates. A tenant can keep a shared address plus one for each full user or employee. Send from the lead or opportunity and the message is logged on that record. Check inbox copies new Microsoft 365 or IMAP mail into the same log.",
        href: "/settings/mailbox",
      },
    ],
  },
  {
    id: "sales",
    title: "10. Sales — quote to cash",
    summary:
      "Customer master, price lists, quotations, orders, deliveries, returns, invoices, receipts, credit ageing, and recurring contracts.",
    audience: ["operations", "finance", "admin"],
    steps: [
      {
        title: "Customers and prices",
        detail:
          "Create the customer with credit limit, payment terms, and tax IDs. Maintain price lists for quotes and orders.",
        href: "/sales/customers",
      },
      {
        title: "Quote, then order",
        detail:
          "A quotation is a price offer. Accept it and convert it to a sales order. Confirm the order before delivery.",
        href: "/sales/quotes",
      },
      {
        title: "Deliver and invoice",
        detail:
          "Delivery notes dispatch a confirmed order. AR invoices follow the order. Submit and approve, then record the receipt. Returns and RMAs reverse a delivery.",
        href: "/sales/orders",
      },
      {
        title: "Credit and recurring billing",
        detail:
          "Credit aging shows open customer balances. A recurring contract generates draft AR invoices on its schedule.",
        href: "/sales/credit",
      },
    ],
    tips: [
      "Approving an AR invoice can create an FBR e-invoice draft.",
      "A confirmed sales order can raise a warehouse pick list.",
    ],
  },
  {
    id: "inventory",
    title: "11. Inventory and warehouse",
    summary:
      "Warehouses, items, bins, stock, movements, stocktake, lots, batches, serials, and pick lists.",
    audience: ["operations", "admin"],
    steps: [
      {
        title: "Warehouses, bins, and items",
        detail:
          "Create a warehouse, then bins inside it. Items are the product and material master. Print a barcode or QR label from the item.",
        href: "/inventory/items",
      },
      {
        title: "Stock and movements",
        detail:
          "Stock levels show on-hand quantity. Movements cover receipts, issues, adjustments, and transfers.",
        href: "/inventory/stock",
      },
      {
        title: "Trace lots and serials",
        detail:
          "Lots hold a lot or batch number. Warehouse batches hold lot quantity by warehouse. Serial numbers trace a single unit.",
        href: "/inventory/lots",
      },
      {
        title: "Count and pick",
        detail:
          "Stocktake adjusts the book to the count. A pick list pulls lines from a confirmed sales order.",
        href: "/inventory/pick-lists",
      },
    ],
  },
  {
    id: "procurement",
    title: "12. Procurement — requisition to vendor bill",
    summary:
      "Demand, vendor quotes, purchase orders, goods receipts, returns, landed cost, then accounts payable.",
    audience: ["operations", "finance", "admin"],
    steps: [
      {
        title: "Raise a requisition",
        detail: "Purchase requisitions go through approval, then convert to a purchase order.",
        href: "/procurement/requisitions",
      },
      {
        title: "Ask vendors, then order",
        detail:
          "Vendor RFQ collects prices. The purchase order is submit, approve, then goods receipt, then an AP invoice.",
        href: "/procurement/orders",
      },
      {
        title: "Receive, return, and land cost",
        detail:
          "Goods receipts post stock against the order. Purchase returns send stock back. Landed cost spreads freight and duty onto the receipt.",
        href: "/procurement/receipts",
      },
    ],
    tips: ["Vendors and AP invoices are shared with Finance."],
  },
  {
    id: "projects",
    title: "13. Projects, time, and job cost",
    summary: "A project, its tasks, timesheets, and cost entries.",
    audience: ["operations", "finance", "admin"],
    steps: [
      {
        title: "Open a project",
        detail: "Projects hold the job. Tasks are the work breakdown.",
        href: "/projects",
      },
      {
        title: "Log time",
        detail:
          "Timesheets: log hours, submit, then approve. Approval updates the task hours. A workflow can drive timesheet approval.",
        href: "/projects/timesheets",
      },
      {
        title: "Record cost",
        detail: "Project costs are job-cost entries against the project.",
        href: "/projects/costs",
      },
    ],
    tips: ["Project tasks are the job plan. Governance → Tasks are workflow assignments, a different list."],
  },
  {
    id: "manufacturing",
    title: "14. Manufacturing",
    summary: "Bills of materials and work orders that issue components and receive finished goods.",
    audience: ["operations", "admin"],
    steps: [
      {
        title: "Define the recipe",
        detail: "Manufacturing → BOMs. A bill of materials is the finished-goods recipe.",
        href: "/mfg/boms",
      },
      {
        title: "Release and complete",
        detail:
          "Work orders: release the order, then complete it. Complete issues components and receipts the finished good into stock.",
        href: "/mfg/work-orders",
      },
    ],
  },
  {
    id: "quality",
    title: "15. Quality — inspect, report, correct",
    summary: "Inspections, non-conformance reports, and corrective and preventive actions.",
    audience: ["operations", "admin"],
    steps: [
      {
        title: "Inspect",
        detail: "Record incoming or in-process inspection results.",
        href: "/qms/inspections",
      },
      {
        title: "Raise an NCR",
        detail: "A non-conformance report is investigated, dispositioned, and closed.",
        href: "/qms/ncrs",
      },
      {
        title: "Open a CAPA",
        detail: "Corrective and preventive actions link back to the NCR.",
        href: "/qms/capas",
      },
    ],
  },
  {
    id: "maintenance",
    title: "16. Maintenance",
    summary: "Corrective work orders and preventive schedules that generate the next order.",
    audience: ["operations", "admin"],
    steps: [
      {
        title: "Log a work order",
        detail: "Maintenance → Work orders covers corrective and preventive jobs on assets.",
        href: "/finance/maintenance-orders",
      },
      {
        title: "Schedule preventive work",
        detail: "PM schedules define the cycle and generate a work order when it is due.",
        href: "/finance/pm-schedules",
      },
    ],
  },
  {
    id: "service",
    title: "17. Customer service",
    summary: "Helpdesk cases and notes, separate from platform support tickets.",
    audience: ["operations", "admin"],
    steps: [
      {
        title: "Open a case",
        detail: "Assign the case, work it, resolve it, and close it.",
        href: "/service/cases",
      },
      {
        title: "Add notes",
        detail: "Case notes can be internal or visible to the customer.",
        href: "/service/notes",
      },
    ],
    tips: ["SaaS → Support tickets is the channel to the platform operator, not this helpdesk."],
  },
  {
    id: "contracts",
    title: "18. Commercial contracts",
    summary: "Agreements kept as their own register, separate from recurring AR billing contracts.",
    audience: ["operations", "finance", "admin"],
    steps: [
      {
        title: "Register the agreement",
        detail: "Contracts stores the commercial agreement, parties, and dates.",
        href: "/contracts",
      },
      {
        title: "File the signed copy",
        detail:
          "Put the signed file in Documents and set Related module to contracts so the file and the register stay linked.",
        href: "/dms/documents",
      },
    ],
  },
  {
    id: "documents",
    title: "19. Documents",
    summary:
      "Folders, types, tags, metadata, versions, checkout, access limits, and Microsoft 365 save.",
    audience: ["operations", "admin", "finance", "hr"],
    steps: [
      {
        title: "Set up cabinets",
        detail:
          "Create folders (including a parent folder), document types such as Policy or Contract, tags, and metadata fields such as Author or Expiry.",
        href: "/dms/folders",
      },
      {
        title: "Add a document",
        detail:
          "Documents → Add. Set title, type, folder, language, and source. Upload the file on the detail page. A new upload becomes the next version. Check out a file before you edit it.",
        href: "/dms/documents",
      },
      {
        title: "Save from Microsoft 365",
        detail:
          "On the document list, Save from Microsoft 365 pulls a file from the configured drive folder. On the document, Save to Microsoft 365 writes the current file back. This path supports files up to 4 MB.",
      },
      {
        title: "Limit who can open it",
        detail:
          "Turn on Restrict to granted users when the file should stay off the general list. Link a document to another record with Related module and Related record ID.",
      },
    ],
    tips: [
          "The connector is Settings → Integrations → Microsoft 365 · OneDrive / SharePoint. It needs tenant id, client id, client secret, mailbox, and folder path (for example SIERP), plus Files.ReadWrite.All and admin consent.",
      "Duplicate detection uses the file checksum.",
    ],
  },
  {
    id: "workflows",
    title: "20. Workflows for any record",
    summary:
      "States, transitions, events, fields, triggers, actions, escalation, and a circle diagram you can export or print.",
    audience: ["admin", "operations", "finance", "hr", "payroll"],
    steps: [
      {
        title: "Create the workflow",
        detail:
          "Documents → Workflows, or Governance → Workflows. Name it, pick Applies to (documents, journals, budgets, vendor invoices, customer invoices, sales orders, requisitions, purchase orders, leave, recruitment, performance, payroll periods, loans, or timesheets), and leave it active.",
        href: "/dms/workflows",
      },
      {
        title: "Build the path",
        detail:
          "On the row menu open States, Transitions, Events, Fields, Triggers, Actions, Escalations, and Records. Name a transition Submit, Approve, Reject, or Post so that desk uses the workflow. Put hours on a state when it should escalate.",
      },
      {
        title: "Choose what happens on a step",
        detail:
          "An action can notify people, notify a role, add a comment, or create a task. Events fire when a record is created, updated, submitted, approved, rejected, or posted. Fields collect extra answers on a transition.",
      },
      {
        title: "Arrange, export, and print",
        detail:
          "View opens the circle diagram. Drag the circles, then use Export SVG, Export PNG, or Print. Reset layout returns the automatic spacing. Dashed arrows are escalations.",
      },
    ],
    tips: [
      "Document control is the ready-made document workflow: Draft, In review (48 hours), Published, Archived, with a signature on the review step.",
      "The person who submitted a step cannot approve that same step when segregation of duties is on. Organization owners do not skip that rule.",
      "Use standard workflow on the list only when you want the document-control template.",
    ],
  },
  {
    id: "workbench",
    title: "21. Notifications, comments, and tasks",
    summary:
      "Internal notices, comments on any record, and tasks created by you or by a workflow.",
    audience: ["all", "admin"],
    steps: [
      {
        title: "Talk inside the organization",
        detail:
          "Governance → Chat, or Employee portal → Chat. Start a direct message, or create a group and invite colleagues. An invite stays pending until they accept. Owners and admins can rename the group, add admins, and remove members. Messages stay in this organization.",
        href: "/chat",
      },
      {
        title: "Read notifications",
        detail:
          "The header bell and Governance → Notifications list workflow, comment, and task messages. Mark a row read when you have acted on it.",
        href: "/inbox",
      },
      {
        title: "Comment on a record",
        detail:
          "Governance → Comments. Choose the record type and the record id, then post. Workflow action “add comment” writes here too, and on the document when the record is a document.",
        href: "/comments",
      },
      {
        title: "Complete a task",
        detail:
          "Governance → Tasks lists work assigned to you or to your role. Owners see every task in the organization. Complete marks it done.",
        href: "/tasks",
      },
    ],
    tips: ["These three lists are internal. They are separate from email and from the Approvals inbox."],
  },
  {
    id: "hr-enterprise",
    title: "22. HR lifecycle",
    summary:
      "Employee master, leave policy, probation, exit, recruitment hire, job history, documents, and training.",
    audience: ["hr", "admin", "finance"],
    steps: [
      {
        title: "Employee master and ESS link",
        detail:
          "Capture CNIC, NTN, EOBI, bank IBAN, contract type, and manager. Link the login user for ESS. Open the employee view for leave, attendance, and document expiry.",
        href: "/hr/employees",
      },
      {
        title: "Leave types and balances",
        detail:
          "Configure accrual, weekend and holiday exclusion, and carry-forward. Accrue year and carry-forward sit under Leave balances. Charged days are working days.",
        href: "/hr/leave-types",
      },
      {
        title: "Probation and separations",
        detail:
          "Confirm, extend, or fail probation. Separations seed a clearance checklist. Settle marks the employee separated and unlinks ESS.",
        href: "/hr/probation",
      },
      {
        title: "Hire from recruitment",
        detail:
          "On an offer, hire creates the employee in probation, leave balances, and a hire line on job history. Fill candidate name, email, department, and designation first.",
        href: "/hr/recruitment",
      },
      {
        title: "Job history and the document matrix",
        detail:
          "Career changes log department, designation, salary, and status. The document matrix lists required types. A missing or expired document flagged as blocking skips payroll generation.",
        href: "/hr/job-history",
      },
      {
        title: "Training",
        detail:
          "Courses carry hours, a mandatory flag, and certificate validity. Enroll the employee and complete the row with certificate number and expiry.",
        href: "/hr/training-courses",
      },
    ],
    tips: [
      "Rejecting or cancelling approved leave restores the balance and clears system on-leave attendance.",
      "Upload employee files and set the expiry date. Verify them against the matrix.",
    ],
  },
  {
    id: "hr",
    title: "23. HR day to day",
    summary:
      "Organization, shifts, overtime, attendance, leave, claims, benefits, performance, and full-and-final settlement.",
    audience: ["hr", "admin"],
    steps: [
      {
        title: "Org structure",
        detail: "Departments and designations, then the employee master.",
        href: "/hr/departments",
      },
      {
        title: "Shifts and overtime",
        detail:
          "Shifts define the work pattern. Overtime policies hold the multiplier. Payroll uses attendance, including overtime.",
        href: "/hr/shifts",
      },
      {
        title: "Attendance and devices",
        detail:
          "Daily records, exceptions, and regularization. Devices cover ZKTeco, Hikvision, Anviz, Suprema, and eSSL. Mark an employee attendance-free when they are exempt.",
        href: "/hr/attendance",
      },
      {
        title: "Leave requests",
        detail: "Approve or reject requests. A workflow on Leave requests can drive the same path.",
        href: "/hr/leaves",
      },
      {
        title: "Claims, benefits, and performance",
        detail:
          "Expense claims are the HR claims desk. Benefit plans and enrollments cover EOBI and similar plans. Performance holds the cycle, self-rating, reviewer, and development plan.",
        href: "/hr/claims",
      },
      {
        title: "Documents and settlement",
        detail:
          "The documents vault stores contracts and certificates for ESS download. F&F settlements are the separation worksheet.",
        href: "/hr/documents",
      },
    ],
  },
  {
    id: "payroll",
    title: "24. Payroll run",
    summary: "Structures, period, generate, approve, mark paid, deliver the slip, and post to the general ledger.",
    audience: ["payroll", "hr", "finance"],
    steps: [
      {
        title: "Salary structures and the period",
        detail: "Define rates, then create the year and month period.",
        href: "/payroll/structures",
      },
      {
        title: "Generate payslips",
        detail:
          "Generation uses structures, loans, and attendance or leave for days worked. Submit, approve, then mark paid. A workflow on Payroll periods can drive approval.",
        href: "/payroll",
      },
      {
        title: "Deliver slips",
        detail:
          "Email through SMTP or Microsoft 365, or the employee opens ESS → Payslips → Print.",
        href: "/ess/payslips",
      },
      {
        title: "Post to the general ledger",
        detail: "Posting creates the salary-expense and statutory-payable journal.",
      },
      {
        title: "Loans",
        detail:
          "Employee loans hold the advance, the schedule, and the payroll deduction flag.",
        href: "/payroll/loans",
      },
    ],
    tips: [
      "Payroll counts work-from-home, half-day, holiday, and paid leave, and posts overtime from the overtime policy.",
      "An employee blocked by the document matrix is skipped.",
    ],
  },
  {
    id: "ess",
    title: "25. Employee Self-Service",
    summary: "Leave, attendance punch, payslips, documents, and the contact fields the employee may edit.",
    audience: ["ess", "hr", "all"],
    steps: [
      {
        title: "Open the portal",
        detail:
          "Go to Employee portal in the nav, or open /ess. ESS-only users land here after login.",
        href: "/ess",
      },
      {
        title: "Request leave",
        detail: "Leave → type, dates, and reason → Submit. Track status on the same page.",
        href: "/ess/leave",
      },
      {
        title: "Check in and out",
        detail:
          "Attendance → Check in or Check out, or log an exception for HR. Exempt staff see a notice instead of the punch buttons.",
        href: "/ess/attendance",
      },
      {
        title: "Payslips and documents",
        detail: "Payslips → Print for the salary slip. Documents → download HR files.",
        href: "/ess/payslips",
      },
      {
        title: "Update contacts",
        detail: "Profile edits phone and email. Other fields stay with HR.",
        href: "/ess/profile",
      },
    ],
    tips: [
      "Allow pop-ups for Print.",
      "If you see “No employee profile linked”, ask HR to link your user to an Employee.",
    ],
  },
  {
    id: "integrations",
    title: "26. Integrations",
    summary:
      "Microsoft 365 mail and files, biometric attendance, bank files, and optional partner connectors.",
    audience: ["integrations", "admin", "hr"],
    steps: [
      {
        title: "Open the hub",
        detail:
          "Settings → Integrations. Opening the page seeds the starter connectors. Recommended connectors are listed first.",
        href: "/settings/integrations",
      },
      {
        title: "Microsoft 365 email",
        detail:
          "Azure app with Mail.Send (application) and admin consent. Add Mail.Read as well if CRM → Mailbox should copy the inbox. Enter tenant id, client id, secret, and sender address. Test the connection.",
      },
      {
        title: "Microsoft 365 files",
        detail:
          "Open Microsoft 365 · OneDrive / SharePoint. It uses Files.ReadWrite.All (application) and admin consent. Set the mailbox and the folder path. Documents then offer Save from Microsoft 365 and Save to Microsoft 365 for files up to 4 MB.",
      },
      {
        title: "SMTP fallback",
        detail:
          "If Graph mail is unavailable, use Settings → Email with smtp.office365.com port 587 and TLS, or another SMTP host. Add a mailbox for the company, a full user, or an employee. IMAP receives mail from Google, Zoho, and other hosts. Email templates hold the message text.",
        href: "/settings/email",
      },
      {
        title: "Calendars",
        detail:
          "Under Calendars, activate Microsoft 365, Google, CalDAV, or any combination. Test each one before enabling it. Microsoft needs Calendars.ReadWrite and the mailbox. Google needs a refresh token. CalDAV needs the calendar collection URL. CRM meetings are then copied there. The SI-ERP calendar remains the record.",
        href: "/settings/integrations",
      },
      {
        title: "Attendance devices and bank files",
        detail:
          "HR → Attendance → Devices, or the attendance connector here. Enable the bank salary-file format for payroll. Optional connectors cover Entra sign-in, Teams, and webhooks when those providers are ready.",
        href: "/hr/attendance",
      },
    ],
    tips: [
      "Store client secrets only in the Integrations screen.",
      "Microsoft 365 mail falls back to the mailbox on the mail connector when the file connector has none.",
    ],
  },
  {
    id: "approvals",
    title: "27. Approvals inbox",
    summary: "Items your role is allowed to approve. Other roles' queues stay off this list.",
    audience: ["finance", "hr", "payroll", "operations", "admin"],
    steps: [
      {
        title: "Open Approvals",
        detail:
          "The list shows only items your role is allowed to approve. Journals, bills, leave, payroll, and the rest stay with the role that holds change on that module, and with the approval matrix when an amount band is set.",
        href: "/approvals",
      },
      {
        title: "Segregation of duties",
        detail:
          "You cannot approve a record you submitted when segregation of duties is enforced. Workflow steps follow the same rule.",
      },
    ],
  },
  {
    id: "governance",
    title: "28. Audit, numbering, security, and import",
    summary: "Who changed a record, how numbers are issued, MFA, operations, and the import hub.",
    audience: ["admin"],
    steps: [
      {
        title: "Read the audit trail",
        detail:
          "Settings → Access, then Audit logs. Each row says who changed a business record and whether the system allowed it. Open a row for the readable detail.",
        href: "/settings/audit",
      },
      {
        title: "Number series and the approval matrix",
        detail:
          "Doc number series sets prefixes and counters. The approval matrix maps an amount band to a role.",
        href: "/settings/doc-series",
      },
      {
        title: "Security and operations",
        detail:
          "MFA / Security turns on TOTP. Operations shows health, SMTP verification, and a database backup request.",
        href: "/settings/security",
      },
      {
        title: "Import hub",
        detail:
          "Download a template, upload one CSV, or upload a ZIP pack. Validate, then commit in dependency order. The pack includes 00_README.txt, numbered CSVs, and manifest.csv in UTF-8.",
        href: "/settings/import-hub",
      },
    ],
    tips: [
      "Email templates are the Templates tab under Settings → Email. Starter templates are already there for a general message, an action, and HR, finance, payroll, billing, sales, and procurement. Edit the wording. The same placeholders work in every template: {{organization}}, {{recipient}}, {{title}}, {{message}}, {{reference}}, {{due_date}}, and {{link}}.",
      "Domain, logo, and colors are under Domain & branding. Tenant PayFast is for company-collected payments.",
    ],
  },
  {
    id: "saas",
    title: "29. Billing, support, and branding",
    summary: "Your subscription invoices, tickets to the platform, and the look of the tenant.",
    audience: ["admin"],
    steps: [
      { title: "Billing", detail: "SaaS invoices and plan status.", href: "/billing" },
      {
        title: "Support tickets",
        detail: "Raise a ticket for the platform operator.",
        href: "/support",
      },
      {
        title: "Domain and branding",
        detail: "Custom domain, logo, and colors, applied on login and in the app.",
        href: "/settings/domain",
      },
    ],
  },
  {
    id: "platform",
    title: "30. Platform operator",
    summary: "Packages, tenants, invoices, staff, domains, and platform mail — platform staff only.",
    audience: ["platform"],
    steps: [
      {
        title: "Control center",
        detail: "Tenant health, packages, billing, and support.",
        href: "/platform",
      },
      {
        title: "Packages and tenants",
        detail: "Seats, modules, and pricing per plan, then the organizations on this platform.",
        href: "/platform/packages",
      },
      {
        title: "Platform mail and PayFast",
        detail:
          "Platform SMTP sends signup and billing mail. Platform PayFast collects subscription payments.",
        href: "/settings/platform-smtp",
      },
    ],
  },
  {
    id: "crud",
    title: "31. Lists, the ⋮ menu, and confirmations",
    summary: "The same pattern on almost every list.",
    audience: ["all", "admin", "finance", "hr", "payroll", "operations"],
    steps: [
      { title: "Create", detail: "Use Add. Required fields are marked. Most records open a full page, not a small dialog." },
      { title: "View, edit, delete", detail: "Row ⋮ → View, Edit, or Delete. Delete asks you to confirm." },
      { title: "Bulk delete", detail: "Select rows, then bulk delete, then confirm." },
      {
        title: "Workflow buttons",
        detail: "Submit, Approve, Reject, and Post appear on desks that support them.",
      },
    ],
  },
  {
    id: "migrate",
    title: "32. Bring opening data in",
    summary: "Use Import hub in the app. The server command remains for an operator who already has CSV files on the host.",
    audience: ["admin", "platform"],
    steps: [
      {
        title: "Use Import hub",
        detail:
          "Settings → Company, then Import. Download templates or a ZIP pack, upload, validate, then commit. Order follows the manifest.",
        href: "/settings/import-hub",
      },
      {
        title: "Operator command",
        detail:
          "On the API host: docker exec -w /app jmc_api python manage.py import_masters --org <code> --coa coa.csv … Files cover chart of accounts, employees, vendors, leave balances, assets, and opening journals.",
      },
      {
        title: "Check the result",
        detail: "Spot-check the chart of accounts, employees, balances, and opening journals in the app.",
      },
    ],
  },
];

export const GUIDE_AUDIENCE_LABELS: Record<GuideAudience, string> = {
  all: "Everyone",
  admin: "Admin",
  finance: "Finance",
  hr: "HR",
  payroll: "Payroll",
  operations: "Operations",
  ess: "ESS",
  integrations: "Integrations",
  platform: "Platform",
};
