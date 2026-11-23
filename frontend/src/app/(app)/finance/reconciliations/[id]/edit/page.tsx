"use client";

import { useParams } from "next/navigation";
import ReconciliationForm from "../../ReconciliationForm";

export default function Page() {
  const params = useParams();
  return <ReconciliationForm mode="edit" id={String(params.id)} />;
}
