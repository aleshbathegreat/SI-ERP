"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Alert, Link as MuiLink } from "@mui/material";
import api from "@/lib/api";

type Hit = {
  leads: { id: number; name: string; company: string; status: string }[];
  customers: { id: number; name: string; code: string }[];
};

type Props = {
  email?: unknown;
  phone?: unknown;
  company?: unknown;
  excludeId?: number;
};

export default function LeadDuplicateHint({ email, phone, company, excludeId }: Props) {
  const [hits, setHits] = useState<Hit | null>(null);

  useEffect(() => {
    const emailText = String(email || "").trim();
    const phoneText = String(phone || "").trim();
    const companyText = String(company || "").trim();
    const phoneDigits = phoneText.replace(/\D/g, "");
    if (emailText.length < 5 && phoneDigits.length < 7 && companyText.length < 3) {
      setHits(null);
      return;
    }
    const timer = window.setTimeout(() => {
      const params = new URLSearchParams();
      if (emailText.includes("@")) params.set("email", emailText);
      if (phoneDigits.length >= 7) params.set("phone", phoneText);
      if (companyText.length >= 3) params.set("company", companyText);
      if (excludeId) params.set("exclude", String(excludeId));
      if ([...params.keys()].length === 0 || (excludeId && [...params.keys()].length === 1)) {
        setHits(null);
        return;
      }
      api
        .get<Hit>(`/crm/leads/check-duplicate/?${params.toString()}`)
        .then((res) => setHits(res.data))
        .catch(() => setHits(null));
    }, 400);
    return () => window.clearTimeout(timer);
  }, [email, phone, company, excludeId]);

  if (!hits || (hits.leads.length === 0 && hits.customers.length === 0)) return null;

  return (
    <Alert severity="warning" sx={{ mt: 2 }}>
      This may already be in the company.
      {hits.leads.map((lead) => (
        <span key={`lead-${lead.id}`}>
          {" "}
          <MuiLink component={Link} href={`/crm/leads/${lead.id}`}>
            Lead {lead.name}
            {lead.company ? ` · ${lead.company}` : ""}
          </MuiLink>
        </span>
      ))}
      {hits.customers.map((customer) => (
        <span key={`customer-${customer.id}`}>
          {" "}
          <MuiLink component={Link} href={`/sales/customers/${customer.id}`}>
            Customer {customer.code} · {customer.name}
          </MuiLink>
        </span>
      ))}
    </Alert>
  );
}
