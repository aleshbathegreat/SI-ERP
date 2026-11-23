export type LegalPage = {
  slug: string;
  title: string;
  description: string;
  updated: string;
  sections: { heading: string; paragraphs: string[]; bullets?: string[] }[];
};

const UPDATED = "2 November 2026";

export const LEGAL_PAGES: LegalPage[] = [
  {
    slug: "privacy",
    title: "Privacy notice",
    description: "What SI-ERP collects, why, and who to write to.",
    updated: UPDATED,
    sections: [
      {
        heading: "Who we are",
        paragraphs: [
          "SI-ERP is a cloud business system operated by SI Global (SIGBL), also presented in the product as A-Symmetric ICT Solutions. The service is published at https://si-erp.mushaz.com.",
          "Privacy questions go to info@sigbl.com. Post is accepted at The Plaza, 3rd Floor, Office 311 and 315, KDA Scheme 5, near II Talwar, Clifton, Karachi, and at Office 13, 8th Floor, Arfa Software Technology Park, 346-B Ferozepur Road, Lahore.",
        ],
      },
      {
        heading: "What we collect",
        paragraphs: [
          "When a company opens a trial or a paid workspace, we collect the company name, a username, a work email, an optional phone number, and the password the owner sets. After sign-in, the workspace holds the business records that company chooses to enter: finance, sales, inventory, people, payroll, documents, and workflow history.",
          "We also keep technical records needed to run the service: sign-in time, the organization the user belongs to, and the audit trail of changes inside that organization.",
        ],
      },
      {
        heading: "Why we use it",
        paragraphs: ["We use this information to:"],
        bullets: [
          "Open and operate the company’s workspace.",
          "Authenticate users, end a session after 24 hours, and support optional multi-factor sign-in.",
          "Apply roles, approvals, and the audit trail.",
          "Send service messages about the workspace, billing, and support.",
          "Protect the service against abuse and to answer a lawful request.",
        ],
      },
      {
        heading: "Who can see it",
        paragraphs: [
          "Business records are scoped to the organization. Users see what their role allows. SI Global staff can access a workspace only to operate, support, or secure the service, or when the customer asks.",
          "We do not sell personal information. We do not use the contents of a customer ledger to advertise to other companies.",
        ],
      },
      {
        heading: "How long we keep it",
        paragraphs: [
          "Workspace data stays for the life of the subscription and for a reasonable period after it ends so the company can export what it needs and so we can meet accounting and legal duties. Sign-in sessions are limited to 24 hours. You may ask us to delete a user or, at the end of the contract, the organization, by writing to info@sigbl.com. We may retain what the law requires us to keep.",
        ],
      },
      {
        heading: "Your requests",
        paragraphs: [
          "A person whose information is in a workspace may ask for a copy, a correction, or a deletion, subject to the company’s own employment and accounting duties. Write to info@sigbl.com. If the record belongs to a customer company, we will usually direct the request to that company’s administrator.",
        ],
      },
      {
        heading: "Children",
        paragraphs: [
          "SI-ERP is a workplace system. It is not directed at children, and a company must not open an account for a child.",
        ],
      },
    ],
  },
  {
    slug: "terms",
    title: "Terms of service",
    description: "The contract for using the SI-ERP workspace.",
    updated: UPDATED,
    sections: [
      {
        heading: "The service",
        paragraphs: [
          "These terms are between the customer company and SI Global (SIGBL) for use of SI-ERP at https://si-erp.mushaz.com. The person who creates the company workspace confirms they are allowed to bind that company.",
          "SI-ERP provides finance, commercial, plant, people, document, and workflow tools inside one organization. Features can change as the product is improved. A material removal of a function a paying customer relies on will be notified in the product or by email.",
        ],
      },
      {
        heading: "Trial and plans",
        paragraphs: [
          "A new company starts on a 14-day trial. The trial does not ask for a card. When the trial ends, the workspace stays available only if the company moves to a paid plan.",
          "Paid plans are Monthly, Annual, and Enterprise, priced in Pakistani rupees as shown on the plans page at the time of purchase. The Annual plan is billed once a year. The Enterprise plan is an annual seat pack with priority support. Seat limits on the plan (functional users and employee self-service users) are part of the plan.",
          "Fees are for the period purchased. A trial has no fee. Unless a written order says otherwise, fees already due for a started period are not refunded. The company may choose not to renew by writing to info@sigbl.com before the next period starts.",
        ],
      },
      {
        heading: "Customer duties",
        paragraphs: ["The customer will:"],
        bullets: [
          "Keep usernames and passwords inside the company, and turn on multi-factor sign-in for finance and payroll roles.",
          "Put only lawful business data into the workspace.",
          "Decide who inside the company may approve, post payroll, and publish documents.",
          "Export the reports and documents it needs for its own statutory record.",
          "Give us a working email for service notices.",
        ],
      },
      {
        heading: "Acceptable use",
        paragraphs: [
          "The workspace may not be used to break the law, to probe or disrupt the service, to upload malware, or to store data the customer has no right to hold. The acceptable use page is part of these terms. We may suspend access that puts other customers or the service at risk, and we will say why unless the law stops us.",
        ],
      },
      {
        heading: "Customer data",
        paragraphs: [
          "The customer keeps ownership of the business data it enters. We host and process it to provide SI-ERP. The privacy notice and the data processing page describe that work. The customer is responsible for the lawfulness of employee, customer, and vendor data it uploads.",
        ],
      },
      {
        heading: "Availability and support",
        paragraphs: [
          "We run the service with reasonable care. We do not promise uninterrupted uptime. Planned maintenance and failures at the network edge can interrupt access. Enterprise priority support means a faster human reply on implementation and product questions. It is not a guaranteed response time unless a separate order states one.",
          "Microsoft 365 save is an optional connector. The standard save sends files up to 4 MB. Larger files need a different transfer, which the product will refuse rather than pretend to store.",
        ],
      },
      {
        heading: "Liability",
        paragraphs: [
          "SI-ERP is a record system. It does not replace the company’s accountant, tax adviser, or lawyer, and it does not file a return with a tax authority by itself unless a screen in the product clearly performs that filing.",
          "To the extent Pakistani law allows, we are not liable for lost profit, lost data caused by the customer’s own users, or indirect loss. Our total liability for a claim arising in a contract year is limited to the fees the customer paid for SI-ERP in that year. Nothing in these terms limits liability for fraud or for death or personal injury caused by negligence.",
        ],
      },
      {
        heading: "Law",
        paragraphs: [
          "These terms are governed by the laws of Pakistan. The courts of Karachi have jurisdiction, without taking away a right the law does not allow us to take away.",
        ],
      },
    ],
  },
  {
    slug: "cookies",
    title: "Cookie notice",
    description: "What the browser stores when you use SI-ERP.",
    updated: UPDATED,
    sections: [
      {
        heading: "Sign-in state",
        paragraphs: [
          "After a successful sign-in, SI-ERP stores the session in the browser’s local storage so the workspace can be opened again. The session is built to end 24 hours after sign-in. Signing out, or reaching that limit, clears it. This storage is required for the product to work. It is not used to advertise.",
        ],
      },
      {
        heading: "Delivery",
        paragraphs: [
          "The public site is delivered through Cloudflare. Cloudflare may set a cookie that is needed to route traffic and to reduce abuse. We do not add an advertising or social-media tracker on the marketing pages.",
        ],
      },
      {
        heading: "Preferences",
        paragraphs: [
          "If you dismiss the short notice on the marketing pages, the browser remembers that choice in local storage. The workspace may also remember display choices such as light or dark mode.",
        ],
      },
      {
        heading: "Control",
        paragraphs: [
          "You can clear site data in the browser. Clearing it signs you out. Blocking storage will stop sign-in from staying open. Questions: info@sigbl.com.",
        ],
      },
    ],
  },
  {
    slug: "acceptable-use",
    title: "Acceptable use",
    description: "What a company may and may not do with a SI-ERP workspace.",
    updated: UPDATED,
    sections: [
      {
        heading: "Permitted use",
        paragraphs: [
          "A workspace is for the customer’s own business: its ledgers, people, stock, documents, and approvals. Users must be real people the customer has authorized, or system accounts the customer controls.",
        ],
      },
      {
        heading: "Not permitted",
        paragraphs: ["A customer or user must not:"],
        bullets: [
          "Attempt to enter another organization’s data.",
          "Probe, scan, or overload the service, except a test we have agreed in writing.",
          "Upload malware or content that is unlawful in Pakistan.",
          "Use the product to send unsolicited bulk email.",
          "Share a single paid seat in a way that hides who approved a financial or payroll action.",
          "Misrepresent SI-ERP as a government filing channel.",
        ],
      },
      {
        heading: "If this is broken",
        paragraphs: [
          "We may remove the offending content, reset access, or suspend the workspace. We will restore access when the risk is gone. A suspension does not by itself erase the customer’s data.",
        ],
      },
    ],
  },
  {
    slug: "data-processing",
    title: "Data processing",
    description: "How customer business data is handled inside SI-ERP.",
    updated: UPDATED,
    sections: [
      {
        heading: "Roles",
        paragraphs: [
          "The customer decides what business and employee data is entered and why. SI Global processes that data to host SI-ERP, to authenticate users, to keep the audit trail, and to provide support the customer asks for.",
        ],
      },
      {
        heading: "Scope",
        paragraphs: ["Processing covers the records the product stores, including:"],
        bullets: [
          "Organization profile, users, roles, and sign-in events.",
          "Finance, sales, procurement, inventory, manufacturing, quality, and projects.",
          "HR, attendance, leave, and payroll.",
          "Documents, versions, comments, tasks, and workflow history.",
        ],
      },
      {
        heading: "Safeguards we actually operate",
        paragraphs: [
          "Access to the application is over HTTPS. A session ends 24 hours after sign-in. Roles limit what a user can open. Document control can require a different person to review than the person who drafted. Optional multi-factor sign-in is available under security settings. The audit trail records changes in language a person can read.",
          "We do not claim an ISO or SOC certificate on this page. If a customer needs a specific control, ask info@sigbl.com and we will say whether it is in the product today.",
        ],
      },
      {
        heading: "Subprocessors",
        paragraphs: [
          "Cloudflare delivers the public site and the API edge. Microsoft is used only if the customer connects Microsoft 365 and chooses to save a file there. We do not send the ledger to an advertising network.",
        ],
      },
      {
        heading: "Return and deletion",
        paragraphs: [
          "During the contract the customer can export the reports and documents its users can open. At the end of the contract the customer may ask, by email to info@sigbl.com, for a copy of its organization data and for deletion after that copy is confirmed. We may retain a limited record of the contract and of invoices we issued.",
        ],
      },
      {
        heading: "Incidents",
        paragraphs: [
          "If we confirm unauthorized access to a customer’s workspace, we will tell the customer’s administrator without undue delay, describe what we know, and say what we are doing about it.",
        ],
      },
    ],
  },
];

export function legalBySlug(slug: string) {
  return LEGAL_PAGES.find((p) => p.slug === slug);
}
