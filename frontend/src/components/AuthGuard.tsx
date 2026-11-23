"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Box, CircularProgress } from "@mui/material";
import { endSession, sessionExpired } from "@/lib/session";
import { useAppSelector } from "@/store/hooks";

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const access = useAppSelector((s) => s.auth.access);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setReady(true);
    const kick = () => {
      if (sessionExpired()) {
        endSession();
        return;
      }
      const token = localStorage.getItem("access_token");
      if (!token && !access) router.replace("/login");
    };
    kick();
    const id = window.setInterval(kick, 30_000);
    document.addEventListener("visibilitychange", kick);
    return () => {
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", kick);
    };
  }, [access, router]);

  if (!ready) {
    return (
      <Box sx={{ display: "grid", placeItems: "center", minHeight: "60vh" }}>
        <CircularProgress />
      </Box>
    );
  }

  return <>{children}</>;
}
