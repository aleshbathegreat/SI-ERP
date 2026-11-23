"use client";

import { useEffect, useRef } from "react";
import { Provider } from "react-redux";
import CloseIcon from "@mui/icons-material/Close";
import { IconButton } from "@mui/material";
import { SnackbarProvider, closeSnackbar } from "notistack";
import { makeStore, AppStore } from "@/store";
import {
  hydrateAuth,
  loginSuccess,
  setOrganization,
  setPermissions,
  setPlatformCaps,
} from "@/store/auth/slice";
import { ColorModeProvider } from "@/theme/ColorModeContext";
import { BrandingProvider } from "@/components/BrandingProvider";
import api from "@/lib/api";
import { endSession, sessionExpired } from "@/lib/session";
import type { Organization, PermissionsMap, User } from "@/store/auth/types";

export default function Providers({ children }: { children: React.ReactNode }) {
  const storeRef = useRef<AppStore | null>(null);
  if (!storeRef.current) {
    storeRef.current = makeStore();
  }

  useEffect(() => {
    if (sessionExpired()) {
      endSession();
      storeRef.current?.dispatch(
        hydrateAuth({
          access: null,
          refresh: null,
          user: null,
          organization: null,
          subscriptionOpen: true,
          permissions: {},
          isPlatformUser: false,
          platformRole: null,
          platformCapabilities: [],
        })
      );
      return;
    }
    const access = localStorage.getItem("access_token");
    const refresh = localStorage.getItem("refresh_token");
    const rawUser = localStorage.getItem("user");
    const rawOrg = localStorage.getItem("organization");
    const rawPerms = localStorage.getItem("permissions");
    let user: User | null = null;
    let organization: Organization | null = null;
    let permissions: PermissionsMap = {};
    if (rawUser) {
      try {
        user = JSON.parse(rawUser) as User;
      } catch {
        user = null;
      }
    }
    if (rawOrg && rawOrg !== "null") {
      try {
        organization = JSON.parse(rawOrg) as Organization;
      } catch {
        organization = null;
      }
    }
    if (rawPerms) {
      try {
        permissions = JSON.parse(rawPerms) as PermissionsMap;
      } catch {
        permissions = user?.permissions || {};
      }
    } else {
      permissions = user?.permissions || {};
    }
    let platformCapabilities: string[] = [];
    try {
      platformCapabilities = JSON.parse(
        localStorage.getItem("platform_capabilities") || "[]"
      );
    } catch {
      platformCapabilities = [];
    }
    storeRef.current?.dispatch(
      hydrateAuth({
        access,
        refresh,
        user,
        organization,
        subscriptionOpen: localStorage.getItem("subscription_open") !== "false",
        permissions,
        isPlatformUser:
          localStorage.getItem("is_platform_user") === "true" || !!user?.is_superuser,
        platformRole: localStorage.getItem("platform_role") || null,
        platformCapabilities,
      })
    );

    // Refresh live permissions after RBAC / package changes (localStorage goes stale).
    if (!access) return;
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.get<{
          user: User;
          organization?: Organization | null;
          subscription_open?: boolean;
          permissions?: PermissionsMap;
          is_platform_user?: boolean;
          platform_role?: string | null;
          platform_capabilities?: string[];
        }>("/auth/me/");
        if (cancelled || !storeRef.current) return;
        const nextPerms = data.permissions || data.user?.permissions || {};
        localStorage.setItem("permissions", JSON.stringify(nextPerms));
        localStorage.setItem("user", JSON.stringify(data.user));
        if (data.organization) {
          localStorage.setItem("organization", JSON.stringify(data.organization));
          storeRef.current.dispatch(setOrganization(data.organization));
        }
        localStorage.setItem(
          "subscription_open",
          String(data.subscription_open ?? true)
        );
        storeRef.current.dispatch(setPermissions(nextPerms));
        storeRef.current.dispatch(
          setPlatformCaps({
            is_platform_user: data.is_platform_user,
            platform_role: data.platform_role,
            platform_capabilities: data.platform_capabilities,
          })
        );
        // Keep access/refresh; refresh user flags (is_owner) from /me.
        storeRef.current.dispatch(
          loginSuccess({
            access,
            refresh: refresh || "",
            user: data.user,
            organization: data.organization,
            subscription_open: data.subscription_open,
            permissions: nextPerms,
            is_platform_user: data.is_platform_user,
            platform_role: data.platform_role,
            platform_capabilities: data.platform_capabilities,
          })
        );
      } catch {
        // Keep hydrated session; 401 interceptor handles logout.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Provider store={storeRef.current}>
      <ColorModeProvider>
        <BrandingProvider>
          <SnackbarProvider
            maxSnack={4}
            autoHideDuration={3500}
            anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
            style={{ maxWidth: 560, whiteSpace: "pre-wrap" }}
            action={(key) => (
              <IconButton
                size="small"
                aria-label="Dismiss"
                color="inherit"
                onMouseDown={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                }}
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  closeSnackbar(key);
                }}
              >
                <CloseIcon fontSize="small" />
              </IconButton>
            )}
          >
            {children}
          </SnackbarProvider>
        </BrandingProvider>
      </ColorModeProvider>
    </Provider>
  );
}
