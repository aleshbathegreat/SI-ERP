import axios from "axios";
import { endSession, sessionExpired } from "@/lib/session";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api",
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const url = String(config.url || "");
    const signingIn =
      url.includes("/auth/login/") ||
      url.includes("/auth/signup/") ||
      url.includes("/auth/password-reset/");
    if (!signingIn && sessionExpired()) {
      endSession();
      return Promise.reject(new Error("Session expired"));
    }
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const status = error.response?.status;
    const original = error.config;

    if (status === 402 && typeof window !== "undefined") {
      localStorage.setItem("subscription_open", "false");
      if (!window.location.pathname.startsWith("/billing")) {
        window.location.href = "/billing";
      }
      return Promise.reject(error);
    }

    const url = String(original?.url || "");
    const signingIn =
      url.includes("/auth/login/") ||
      url.includes("/auth/signup/") ||
      url.includes("/auth/password-reset/");
    if (status === 401 && !signingIn && typeof window !== "undefined") {
      if (sessionExpired()) {
        endSession();
        return Promise.reject(error);
      }
      if (original && !original._retry) {
        original._retry = true;
        const refresh = localStorage.getItem("refresh_token");
        if (refresh) {
          try {
            const { data } = await axios.post(
              `${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api"}/auth/refresh/`,
              { refresh }
            );
            if (sessionExpired()) {
              endSession();
              return Promise.reject(error);
            }
            localStorage.setItem("access_token", data.access);
            original.headers.Authorization = `Bearer ${data.access}`;
            return api(original);
          } catch {
            endSession();
          }
        } else {
          endSession();
        }
      }
    }
    return Promise.reject(error);
  }
);

export default api;
