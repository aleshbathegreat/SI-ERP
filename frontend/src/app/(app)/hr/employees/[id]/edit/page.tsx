"use client";

import { useParams } from "next/navigation";
import EmployeeForm from "../../EmployeeForm";

export default function Page() {
  const params = useParams();
  return <EmployeeForm mode="edit" id={String(params.id)} />;
}
