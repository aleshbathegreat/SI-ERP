"use client";

import AssetForm from "../AssetForm";
import { useParams } from "next/navigation";

export default function Page() {
  const params = useParams();
  return <AssetForm mode="view" id={String(params.id)} />;
}
