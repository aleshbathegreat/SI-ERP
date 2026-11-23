"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PLATFORM_LOGO_URL } from "@/lib/branding";
import { LEGAL_PAGES } from "@/lib/legalPages";
import "./site.css";

export default function SiteFrame({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const [stuck, setStuck] = useState(false);
  const [workspace, setWorkspace] = useState(false);
  const [cookieOn, setCookieOn] = useState(false);

  useEffect(() => {
    document.documentElement.classList.add("mk-anim");
    const token = localStorage.getItem("access_token");
    setWorkspace(Boolean(token));
    setCookieOn(localStorage.getItem("mk_cookie_ok") !== "1");
    const onScroll = () => setStuck(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div className="mk">
      <header className={`mk-nav${stuck ? " is-stuck" : ""}${open ? " is-open" : ""}`}>
        <Link href="/" className="mk-brand" onClick={() => setOpen(false)}>
          <img src={PLATFORM_LOGO_URL} alt="SI Global" />
          <span>
            <strong>SI-ERP</strong>
            <span>SI Global · one company system</span>
          </span>
        </Link>
        <nav className="mk-links">
          <a href="/#fit" onClick={() => window.setTimeout(() => setOpen(false), 0)}>Who it fits</a>
          <a href="/#modules" onClick={() => window.setTimeout(() => setOpen(false), 0)}>Modules</a>
          <Link href="/pricing" onClick={() => window.setTimeout(() => setOpen(false), 0)}>Plans</Link>
          <a href="/#security" onClick={() => window.setTimeout(() => setOpen(false), 0)}>Security</a>
        </nav>
        <div className="mk-actions">
          {workspace ? (
            <Link className="mk-btn mk-btn-navy" href="/dashboard">Open workspace</Link>
          ) : (
            <>
              <Link className="mk-btn mk-btn-ghost" href="/login">Sign in</Link>
              <Link className="mk-btn mk-btn-navy" href="/signup">Start trial</Link>
            </>
          )}
          <button className="mk-menu" type="button" aria-label="Menu" onClick={() => setOpen((v) => !v)}>
            <span />
          </button>
        </div>
      </header>
      {children}
      <footer className="mk-foot">
        <div className="mk-foot-grid">
          <div>
            <h4>SI-ERP</h4>
            <p>Finance, people, stock, and documents for a company that has outgrown desktop accounts.</p>
            <p>SI Global (SIGBL) · A-Symmetric ICT Solutions</p>
            <a href="mailto:info@sigbl.com">info@sigbl.com</a>
          </div>
          <div>
            <h4>Product</h4>
            <a href="/#modules">Modules</a>
            <Link href="/pricing">Plans</Link>
            <Link href="/signup">14-day trial</Link>
            <Link href="/login">Sign in</Link>
          </div>
          <div>
            <h4>Offices</h4>
            <p>Clifton, Karachi</p>
            <p>Arfa Software Technology Park, Lahore</p>
            <p>Blue Area, Islamabad</p>
            <a href="https://sigbl.com" target="_blank" rel="noreferrer">sigbl.com</a>
          </div>
          <div>
            <h4>Legal</h4>
            {LEGAL_PAGES.map((p) => (
              <Link key={p.slug} href={`/legal/${p.slug}`}>{p.title}</Link>
            ))}
          </div>
        </div>
        <p className="mk-legal-line">© {new Date().getFullYear()} SI Global. SI-ERP is a business system, not a substitute for your accountant or tax adviser.</p>
      </footer>
      {cookieOn ? (
        <div className="mk-cookie" role="dialog" aria-label="Cookie notice">
          <p>
            Sign-in stays in this browser, and Cloudflare may set a cookie to deliver the site.{" "}
            <Link href="/legal/cookies">Cookie notice</Link>
          </p>
          <button
            className="mk-btn mk-btn-navy"
            type="button"
            onClick={() => {
              localStorage.setItem("mk_cookie_ok", "1");
              setCookieOn(false);
            }}
          >
            OK
          </button>
        </div>
      ) : null}
    </div>
  );
}
