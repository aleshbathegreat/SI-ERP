"use client";

import { useParams } from "next/navigation";
import AttendanceForm from "../../AttendanceForm";

export default function Page() {
  const params = useParams();
  return <AttendanceForm mode="edit" id={String(params.id)} />;
}
