import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import type { AuthState, Organization, PermissionsMap, User } from "./types";

const initialState: AuthState = {
  user: null,
  organization: null,
  subscriptionOpen: true,
  permissions: {},
  access: null,
  refresh: null,
  loading: false,
  error: null,
  isPlatformUser: false,
  platformRole: null,
  platformCapabilities: [],
};

type LoginPayload = {
  access: string;
  refresh: string;
  user: User;
  organization?: Organization | null;
  subscription_open?: boolean;
  permissions?: PermissionsMap;
  is_platform_user?: boolean;
  platform_role?: string | null;
  platform_capabilities?: string[];
};

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    loginRequest(
      state,
      _action: PayloadAction<{ username: string; password: string; mfa_code?: string }>
    ) {
      state.loading = true;
      state.error = null;
    },
    signupRequest(
      state,
      _action: PayloadAction<{
        company_name: string;
        username: string;
        email: string;
        password: string;
        first_name?: string;
        last_name?: string;
        phone?: string;
      }>
    ) {
      state.loading = true;
      state.error = null;
    },
    loginSuccess(state, action: PayloadAction<LoginPayload>) {
      state.loading = false;
      state.access = action.payload.access;
      state.refresh = action.payload.refresh;
      state.user = action.payload.user;
      state.organization =
        action.payload.organization || action.payload.user.profile?.organization || null;
      state.subscriptionOpen = action.payload.subscription_open ?? true;
      state.permissions =
        action.payload.permissions || action.payload.user.permissions || {};
      state.isPlatformUser =
        !!action.payload.is_platform_user || !!action.payload.user.is_superuser;
      state.platformRole =
        action.payload.platform_role ||
        (action.payload.user.is_superuser ? "owner" : null);
      state.platformCapabilities = action.payload.platform_capabilities || [];
      state.error = null;
    },
    loginFailure(state, action: PayloadAction<string>) {
      state.loading = false;
      state.error = action.payload;
    },
    setSubscriptionClosed(state) {
      state.subscriptionOpen = false;
    },
    setOrganization(state, action: PayloadAction<Organization>) {
      state.organization = action.payload;
      state.subscriptionOpen = action.payload.subscription_open ?? true;
    },
    setPermissions(state, action: PayloadAction<PermissionsMap>) {
      state.permissions = action.payload;
    },
    setPlatformCaps(
      state,
      action: PayloadAction<{
        is_platform_user?: boolean;
        platform_role?: string | null;
        platform_capabilities?: string[];
      }>
    ) {
      if (action.payload.is_platform_user != null) {
        state.isPlatformUser = action.payload.is_platform_user;
      }
      if (action.payload.platform_role !== undefined) {
        state.platformRole = action.payload.platform_role;
      }
      if (action.payload.platform_capabilities) {
        state.platformCapabilities = action.payload.platform_capabilities;
      }
    },
    logout(state) {
      Object.assign(state, initialState);
    },
    hydrateAuth(
      state,
      action: PayloadAction<{
        access: string | null;
        refresh: string | null;
        user: User | null;
        organization?: Organization | null;
        subscriptionOpen?: boolean;
        permissions?: PermissionsMap;
        isPlatformUser?: boolean;
        platformRole?: string | null;
        platformCapabilities?: string[];
      }>
    ) {
      state.access = action.payload.access;
      state.refresh = action.payload.refresh;
      state.user = action.payload.user;
      state.organization = action.payload.organization || null;
      state.subscriptionOpen = action.payload.subscriptionOpen ?? true;
      state.permissions =
        action.payload.permissions || action.payload.user?.permissions || {};
      state.isPlatformUser =
        action.payload.isPlatformUser ?? !!action.payload.user?.is_superuser;
      state.platformRole =
        action.payload.platformRole ??
        (action.payload.user?.is_superuser ? "owner" : null);
      state.platformCapabilities = action.payload.platformCapabilities || [];
    },
  },
});

export const {
  loginRequest,
  signupRequest,
  loginSuccess,
  loginFailure,
  logout,
  hydrateAuth,
  setSubscriptionClosed,
  setOrganization,
  setPermissions,
  setPlatformCaps,
} = authSlice.actions;
export default authSlice.reducer;
