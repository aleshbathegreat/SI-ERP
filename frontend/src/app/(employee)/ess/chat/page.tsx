"use client";

import { Suspense } from "react";
import ChatDesk from "@/components/chat/ChatDesk";

export default function EssChatPage() {
  return (
    <Suspense>
      <ChatDesk />
    </Suspense>
  );
}
