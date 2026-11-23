import type { Metadata } from "next";
import Landing from "@/components/marketing/Landing";
import SiteFrame from "@/components/marketing/SiteFrame";

export const metadata: Metadata = {
  title: "SI-ERP — finance, people, and operations",
  description:
    "SI-ERP by SI Global. One workspace for the ledger, payroll, inventory, documents, and approvals. 14-day trial, priced in PKR.",
};

export default function HomePage() {
  return (
    <SiteFrame>
      <Landing />
    </SiteFrame>
  );
}
