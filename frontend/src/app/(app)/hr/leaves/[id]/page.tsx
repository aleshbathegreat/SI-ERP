"use client";

import { useParams } from "next/navigation";
import LeaveForm from "../LeaveForm";

export default function Page() {
  const params = useParams();
  return <LeaveForm mode="view" id={String(params.id)} />;
}
