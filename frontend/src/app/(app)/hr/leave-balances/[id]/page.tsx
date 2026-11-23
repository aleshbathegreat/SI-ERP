"use client";

import { useParams } from "next/navigation";
import LeaveBalanceFormPage from "../LeaveBalanceFormPage";

export default function Page() {
  const params = useParams();
  return <LeaveBalanceFormPage mode="view" id={String(params.id)} />;
}
