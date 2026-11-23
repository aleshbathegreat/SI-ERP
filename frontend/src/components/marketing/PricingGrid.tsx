"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { FALLBACK_PLANS, PlanCard } from "@/lib/marketingContent";

function money(price: string) {
  const n = Number(price);
  if (!Number.isFinite(n)) return price;
  return `PKR ${n.toLocaleString("en-PK")}`;
}

function period(interval: string) {
  if (interval === "year") return "per year";
  if (interval === "month") return "per month";
  return "for 14 days";
}

export default function PricingGrid() {
  const [plans, setPlans] = useState<PlanCard[]>(FALLBACK_PLANS);

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";
    fetch(`${base}/saas/plans/`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("plans"))))
      .then((rows) => {
        if (Array.isArray(rows) && rows.length) setPlans(rows);
      })
      .catch(() => setPlans(FALLBACK_PLANS));
  }, []);

  return (
    <div className="mk-plans">
      {plans.map((p) => (
        <article key={p.code || p.name} className={`mk-plan${p.code === "annual" ? " is-hot" : ""}`}>
          {p.code === "annual" ? <span className="tag">Best fit</span> : null}
          <h3>{p.name}</h3>
          <div className="mk-price">
            {money(p.price)} <span>{period(p.interval)}</span>
          </div>
          <p>{p.summary}</p>
          <ul>
            <li>{p.max_functional_users} functional users</li>
            <li>{p.max_ess_users} employee self-service users</li>
            <li>Finance, HR, payroll, and operations</li>
            <li>{p.code === "enterprise" ? "Priority support" : "Email support"}</li>
          </ul>
          <Link className={`mk-btn ${p.code === "annual" ? "mk-btn-navy" : "mk-btn-ghost"}`} href="/signup">
            {p.code === "trial" ? "Start free trial" : "Start with the trial"}
          </Link>
        </article>
      ))}
    </div>
  );
}
