"use client";

import { useParams } from "next/navigation";
import PayslipForm from "../PayslipForm";

export default function Page() {
  const params = useParams();
  return <PayslipForm mode="view" id={String(params.id)} />;
}
