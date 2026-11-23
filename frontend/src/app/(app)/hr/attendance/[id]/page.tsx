"use client";

import { useParams } from "next/navigation";
import AttendanceForm from "../AttendanceForm";

export default function Page() {
  const params = useParams();
  return <AttendanceForm mode="view" id={String(params.id)} />;
}
