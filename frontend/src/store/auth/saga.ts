import { call, put, takeLatest } from "redux-saga/effects";
import type { PayloadAction } from "@reduxjs/toolkit";
import api from "@/lib/api";
import { stampSession } from "@/lib/session";
import { loginFailure, loginRequest, loginSuccess, signupRequest } from "./slice";
import type { Organization, PermissionsMap, User } from "./types";

type AuthResponse = {
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

function persist(data: AuthResponse) {
  if (typeof window === "undefined") return;
  const permissions = data.permissions || data.user.permissions || {};
  localStorage.setItem("access_token", data.access);
  localStorage.setItem("refresh_token", data.refresh);
  localStorage.setItem("user", JSON.stringify(data.user));
  localStorage.setItem(
    "organization",
    JSON.stringify(data.organization || data.user.profile?.organization || null)
  );
  localStorage.setItem("subscription_open", String(data.subscription_open ?? true));
  localStorage.setItem("permissions", JSON.stringify(permissions));
  localStorage.setItem(
    "is_platform_user",
    String(!!data.is_platform_user || !!data.user.is_superuser)
  );
  localStorage.setItem("platform_role", data.platform_role || "");
  localStorage.setItem(
    "platform_capabilities",
    JSON.stringify(data.platform_capabilities || [])
  );
  stampSession();
}

function* loginWorker(
  action: PayloadAction<{ username: string; password: string; mfa_code?: string }>
) {
  try {
    const { data }: { data: AuthResponse } = yield call(api.post, "/auth/login/", action.payload);
    persist(data);
    yield put(loginSuccess(data));
  } catch (err: unknown) {
    const resp = (err as {
      response?: {
        status?: number;
        data?: { detail?: string | string[]; mfa_required?: boolean };
        headers?: { "retry-after"?: string };
      };
    })?.response;
    const data = resp?.data;
    let message: string;
    if (data?.mfa_required) {
      message = "MFA code required — enter authenticator code";
    } else if (resp?.status === 429) {
      const detail = Array.isArray(data?.detail) ? data.detail[0] : data?.detail;
      const retry = resp.headers?.["retry-after"];
      message =
        (typeof detail === "string" && detail) ||
        (retry
          ? `Too many login attempts. Try again in ${retry}s.`
          : "Too many login attempts. Wait a minute and try again.");
    } else {
      const detail = Array.isArray(data?.detail) ? data.detail[0] : data?.detail;
      message = (typeof detail === "string" && detail) || "Login failed";
    }
    yield put(loginFailure(String(message)));
  }
}

function* signupWorker(
  action: PayloadAction<{
    company_name: string;
    username: string;
    email: string;
    password: string;
    first_name?: string;
    last_name?: string;
    phone?: string;
  }>
) {
  try {
    const { data }: { data: AuthResponse } = yield call(api.post, "/saas/signup/", action.payload);
    persist(data);
    yield put(
      loginSuccess({
        ...data,
        subscription_open: data.subscription_open ?? true,
      })
    );
  } catch (err: unknown) {
    const message =
      (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
      "Signup failed";
    yield put(loginFailure(String(message)));
  }
}

export function* authSaga() {
  yield takeLatest(loginRequest.type, loginWorker);
  yield takeLatest(signupRequest.type, signupWorker);
}
