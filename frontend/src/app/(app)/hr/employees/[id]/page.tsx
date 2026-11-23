"use client";

import { useParams } from "next/navigation";
import EmployeeForm from "../EmployeeForm";

export default function Page() {
  const params = useParams();
  return <EmployeeForm mode="view" id={String(params.id)} />;
}
