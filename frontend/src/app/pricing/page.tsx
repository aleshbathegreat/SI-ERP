import type { Metadata } from "next";
import PricingGrid from "@/components/marketing/PricingGrid";
import SiteFrame from "@/components/marketing/SiteFrame";

export const metadata: Metadata = {
  title: "Plans · SI-ERP",
  description: "SI-ERP trial, monthly, annual, and enterprise plans in Pakistani rupees.",
};

export default function PricingPage() {
  return (
    <SiteFrame>
      <section className="mk-wrap">
        <h1 style={{ fontSize: "clamp(36px, 5vw, 56px)" }}>Plans</h1>
        <p className="mk-sub">
          Every plan opens the same product. The difference is the number of people and the support that comes with the year.
        </p>
        <PricingGrid />
      </section>
    </SiteFrame>
  );
}
