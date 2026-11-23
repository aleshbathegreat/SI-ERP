"use client";

import { useParams } from "next/navigation";
import DocumentForm from "../DocumentForm";

export default function Page() {
  const params = useParams();
  return <DocumentForm mode="view" id={String(params.id)} />;
}
