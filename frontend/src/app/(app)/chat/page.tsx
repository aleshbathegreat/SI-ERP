"use client";

import { Suspense } from "react";
import ModuleGate from "@/components/ModuleGate";
import ChatDesk from "@/components/chat/ChatDesk";

export default function ChatPage() {
  return (
    <ModuleGate module="chat">
      <Suspense>
        <ChatDesk />
      </Suspense>
    </ModuleGate>
  );
}
