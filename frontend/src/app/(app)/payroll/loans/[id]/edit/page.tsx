"use client";

import { useParams } from "next/navigation";
import LoanFormPage from "../../LoanFormPage";

export default function Page() {
  const params = useParams();
  return <LoanFormPage mode="edit" id={String(params.id)} />;
}
