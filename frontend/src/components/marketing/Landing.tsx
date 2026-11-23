"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import PricingGrid from "@/components/marketing/PricingGrid";
import { FIRST_DAYS, FITS, INDUSTRIES, MODULES, ModuleGroup, PILLARS } from "@/lib/marketingContent";

const FILTERS: ("All" | ModuleGroup)[] = ["All", "Finance", "Commercial", "Plant", "People", "Control"];

function Mark({ group }: { group: string }) {
  const paths: Record<string, string> = {
    Finance: "M4 14h12M6 14V6h8v8M8 8h4",
    Commercial: "M4 12l4-6 3 3 5-7M4 16h12",
    Plant: "M5 15V7l5-3 5 3v8M8 15v-4h4v4",
    People: "M8 9a2.2 2.2 0 1 0 0-4.4A2.2 2.2 0 0 0 8 9zm6 0a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM3.5 15c.4-2 2-3 4.5-3s4.1 1 4.5 3M12 12.2c1.6.2 2.8 1.2 3.2 2.8",
    Control: "M9 3.5l5 2v4.2c0 3-2 4.8-5 5.8-3-1-5-2.8-5-5.8V5.5l5-2z",
  };
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
      <path d={paths[group] || paths.Finance} />
    </svg>
  );
}

export default function Landing() {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("All");

  useEffect(() => {
    const nodes = Array.from(document.querySelectorAll(".mk-reveal"));
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-in");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12 }
    );
    nodes.forEach((n) => io.observe(n));
    return () => io.disconnect();
  }, []);

  const loop = [...INDUSTRIES, ...INDUSTRIES];
  const visible = filter === "All" ? MODULES : MODULES.filter((m) => m.group === filter);

  return (
    <>
      <section className="mk-hero">
        <div className="mk-hero-grid">
          <div>
            <div className="mk-kicker"><i /> SI Global · Pakistan</div>
            <h1>One workspace for the company you run.</h1>
            <p className="mk-lead">
              Ledger, payroll, stock, plant, documents, and approvals share one organization.
              Built for a manufacturer, mill, trader, or multi-site firm ready to leave desktop accounts.
            </p>
            <div className="mk-hero-cta">
              <Link className="mk-btn mk-btn-light" href="/signup">Start the 14-day trial</Link>
              <a className="mk-btn mk-btn-line" href="#plans">Compare plans</a>
            </div>
            <div className="mk-metrics">
              <div><strong>PKR 0</strong><span>14 days, no card</span></div>
              <div><strong>PKR 75,000</strong><span>Annual for an operating company</span></div>
              <div><strong>3 cities</strong><span>Karachi, Lahore, Islamabad</span></div>
            </div>
          </div>
          <div className="mk-stage" aria-hidden="true">
            <div className="mk-window">
              <div className="mk-winbar"><i /><i /><i /></div>
              <div className="mk-app">
                <aside className="mk-side">
                  <b>Your company</b>
                  <em className="on">Finance</em>
                  <em>Sales</em>
                  <em>Inventory</em>
                  <em>Payroll</em>
                  <em>Documents</em>
                  <em>Workflows</em>
                </aside>
                <div className="mk-main">
                  <div className="mk-kpis">
                    <div className="mk-kpi"><span>Receivables</span><strong>PKR 4.8m</strong></div>
                    <div className="mk-kpi"><span>Payables</span><strong>PKR 2.1m</strong></div>
                    <div className="mk-kpi"><span>Payroll</span><strong>Posted</strong></div>
                  </div>
                  <div className="mk-chart">
                    <svg viewBox="0 0 280 90" preserveAspectRatio="none">
                      <path d="M0 70 C 30 68, 40 40, 70 46 S 120 20, 150 28 200 62, 230 36 270 18, 280 22" />
                    </svg>
                    <div className="mk-bars">
                      <span style={{ height: "40%" }} />
                      <span style={{ height: "62%", animationDelay: "0.1s" }} />
                      <span style={{ height: "48%", animationDelay: "0.15s" }} />
                      <span style={{ height: "80%", animationDelay: "0.2s" }} />
                      <span style={{ height: "70%", animationDelay: "0.25s" }} />
                      <span style={{ height: "90%", animationDelay: "0.3s" }} />
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div className="mk-float mk-float-b">
              <strong><i className="mk-dot" /> In review</strong>
              <small>Purchase order · 48h escalation</small>
            </div>
            <div className="mk-float mk-float-a">
              <strong>Payroll posted</strong>
              <small>Journal created from the pay run</small>
            </div>
          </div>
        </div>
      </section>

      <div className="mk-band">
        <div className="mk-marquee">
          {loop.map((name, i) => (
            <span key={`${name}-${i}`}>{name}</span>
          ))}
        </div>
      </div>

      <section className="mk-wrap" id="fit">
        <div className="mk-reveal">
          <p className="mk-label">Who it fits</p>
          <h2>Pick the conversation before the demo.</h2>
          <p className="mk-sub">
            The trial opens the same apps a paying company uses. The plan changes the number of people and the support, not the product.
          </p>
        </div>
        <div className="mk-fits">
          {FITS.map((fit) => (
            <article className="mk-fit mk-reveal" key={fit.title}>
              <span>{fit.plan}</span>
              <h3>{fit.title}</h3>
              <p>{fit.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="mk-wrap" id="product" style={{ paddingTop: 0 }}>
        <div className="mk-reveal">
          <p className="mk-label">One organization</p>
          <h2>The close, the pay run, and the file live together.</h2>
          <p className="mk-sub">
            One company subscription in rupees. Finance, the warehouse, and the approver work in the same tenant.
          </p>
        </div>
        <div className="mk-outcomes">
          <article className="mk-outcome mk-reveal">
            <h3>The month closes here</h3>
            <p>Journals, open periods, bank, assets, tax, and the reports finance signs.</p>
          </article>
          <article className="mk-outcome mk-reveal">
            <h3>Payroll posts itself</h3>
            <p>The pay run creates the journal. The employee reads the payslip in self-service.</p>
          </article>
          <article className="mk-outcome mk-reveal">
            <h3>Approval has a name</h3>
            <p>The person who drafts is separate from the person who publishes. The audit trail stays readable.</p>
          </article>
        </div>
        <div className="mk-pillars">
          {PILLARS.map((pillar) => (
            <article className="mk-pillar mk-reveal" key={pillar.title}>
              <div className="mk-ico"><Mark group={pillar.title} /></div>
              <h3>{pillar.title}</h3>
              <ul>
                {pillar.points.map((point) => (
                  <li key={point}>{point}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="mk-wrap" id="modules" style={{ paddingTop: 0 }}>
        <div className="mk-reveal">
          <p className="mk-label">On the floor today</p>
          <h2>Every desk that ships.</h2>
          <p className="mk-sub">Filter by the part of the company you want to see. Each card is a working screen.</p>
        </div>
        <div className="mk-filters" role="tablist" aria-label="Module groups">
          {FILTERS.map((name) => (
            <button
              key={name}
              type="button"
              role="tab"
              aria-selected={filter === name}
              className={filter === name ? "is-on" : ""}
              onClick={() => setFilter(name)}
            >
              {name}
            </button>
          ))}
        </div>
        <div className="mk-index">
          {visible.map((mod) => (
            <article className="mk-mod" key={mod.name}>
              <div className="mk-ico"><Mark group={mod.group} /></div>
              <div>
                <h3>{mod.name}</h3>
                <p>{mod.text}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="mk-wrap" id="workflow">
        <div className="mk-split">
          <div className="mk-panel mk-reveal">
            <div className="mk-kicker" style={{ color: "#9ad7e8" }}><i /> Document control</div>
            <h2 style={{ fontSize: 32, maxWidth: "16ch", marginTop: 12 }}>The signer is a different person from the author.</h2>
            <div className="mk-flow">
              <div className="mk-node">Draft</div>
              <div className="mk-arrow" />
              <div className="mk-node on">In review</div>
              <div className="mk-arrow" />
              <div className="mk-node">Published</div>
              <div className="mk-arrow" />
              <div className="mk-node">Archived</div>
            </div>
            <p style={{ marginTop: 18, color: "#d5e4ee", maxWidth: "46ch" }}>
              The same engine runs journals, vendor bills, sales orders, leave, recruitment, payroll periods, and documents.
              Review that sits for 48 hours escalates. The diagram can be dragged, exported, and printed.
            </p>
          </div>
          <div className="mk-reveal">
            <p className="mk-label">Quote to cash</p>
            <h2>From a quote to a posted journal.</h2>
            <div className="mk-steps">
              <div className="mk-step"><b>1</b><div><strong>Sell</strong><p className="mk-sub">A quote becomes an order, then a customer invoice, against a credit limit.</p></div></div>
              <div className="mk-step"><b>2</b><div><strong>Supply</strong><p className="mk-sub">Pick from the bin, buy what the plant is short of, and inspect before it ships.</p></div></div>
              <div className="mk-step"><b>3</b><div><strong>Pay</strong><p className="mk-sub">The pay run posts to the ledger. The employee reads the payslip in self-service.</p></div></div>
              <div className="mk-step"><b>4</b><div><strong>Keep</strong><p className="mk-sub">The file lives in documents, with versions, a comment, and the person who approved it.</p></div></div>
            </div>
          </div>
        </div>
      </section>

      <section className="mk-wrap" id="start">
        <div className="mk-reveal">
          <p className="mk-label">The first fourteen days</p>
          <h2>A trial with a finish line.</h2>
          <p className="mk-sub">Use the two weeks to run one close with the people who own it. Then keep the year, or stop.</p>
        </div>
        <div className="mk-days">
          {FIRST_DAYS.map((item) => (
            <article className="mk-day mk-reveal" key={item.day}>
              <span>{item.day}</span>
              <h3>{item.title}</h3>
              <p>{item.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="mk-wrap" id="plans">
        <div className="mk-reveal">
          <p className="mk-label">Plans</p>
          <h2>A price for the company.</h2>
          <p className="mk-sub">
            Start on the trial. Monthly proves the close. Annual is the seat pack most operating companies keep. Enterprise is the group with more sites and more people on self-service.
          </p>
        </div>
        <PricingGrid />
      </section>

      <section className="mk-wrap" id="security">
        <div className="mk-secgrid">
          <div className="mk-reveal">
            <p className="mk-label">Controls</p>
            <h2>What a finance director can point at.</h2>
            <p className="mk-sub">
              The controls below are switched on. A certificate is named here only after it is earned.
            </p>
            <div className="mk-checks">
              <div><strong>HTTPS at the edge</strong><span>The site and the API are served over TLS, with the browser protections the host already sends.</span></div>
              <div><strong>A session that ends</strong><span>Sign-in lasts 24 hours from the moment it starts, including the refresh.</span></div>
              <div><strong>Roles and separation</strong><span>A user sees the modules their role allows. Document control can refuse the author as the publisher.</span></div>
              <div><strong>Optional MFA</strong><span>A second factor is available on the security settings of the account.</span></div>
              <div><strong>An audit a person can read</strong><span>Changes are written as history, including access that was denied.</span></div>
            </div>
          </div>
          <div className="mk-faq mk-reveal">
            <details open>
              <summary>Who is this for?</summary>
              <p>A Pakistani operating company with its own NTN, more than one department, and accounts that have outgrown a desktop file. A group already on a global ERP is a later conversation.</p>
            </details>
            <details>
              <summary>Does the trial need a card?</summary>
              <p>No. Create the company, use the workspace for 14 days, and choose a paid plan when the close belongs here.</p>
            </details>
            <details>
              <summary>Where do we ask a question?</summary>
              <p>Write to info@sigbl.com. Enterprise customers get priority on that queue. Offices are in Karachi, Lahore, and Islamabad.</p>
            </details>
            <details>
              <summary>Can we take our data?</summary>
              <p>Users export the reports and documents they can open. At the end of the contract, email info@sigbl.com for a copy of the organization data. The data processing page states the rest.</p>
            </details>
          </div>
        </div>
      </section>

      <section className="mk-close">
        <div>
          <h2>Open the company this week.</h2>
          <p style={{ color: "#d5e4ee", marginTop: 10, maxWidth: "46ch" }}>
            Fourteen days on the real apps. No card. Finance, payroll, and the warehouse share the ledger.
          </p>
        </div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <Link className="mk-btn mk-btn-light" href="/signup">Create the company</Link>
          <Link className="mk-btn mk-btn-line" href="/login">I already have access</Link>
        </div>
      </section>
    </>
  );
}
