"use client";

import { useParams } from "next/navigation";
import PeriodForm from "../../PeriodForm";

export default function Page() {
  const params = useParams();
  return <PeriodForm mode="edit" id={String(params.id)} />;
}
