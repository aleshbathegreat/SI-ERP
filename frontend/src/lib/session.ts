/** Signed-in session lasts 24 hours from login, then the browser returns to /login. */
export const SESSION_MS = 24 * 60 * 60 * 1000;

const EXPIRES_KEY = "session_expires_at";

const AUTH_KEYS = [
  "access_token",
  "refresh_token",
  "user",
  "organization",
  "permissions",
  "subscription_open",
  "is_platform_user",
  "platform_role",
  "platform_capabilities",
  EXPIRES_KEY,
];

function jwtIssuedAt(token: string): number | null {
  try {
    const part = token.split(".")[1];
    if (!part) return null;
    const b64 = part.replace(/-/g, "+").replace(/_/g, "/");
    const padded = b64 + "=".repeat((4 - (b64.length % 4)) % 4);
    const payload = JSON.parse(atob(padded)) as { iat?: unknown };
    return typeof payload.iat === "number" ? payload.iat * 1000 : null;
  } catch {
    return null;
  }
}

export function stampSession(now = Date.now()) {
  localStorage.setItem(EXPIRES_KEY, String(now + SESSION_MS));
}

/** Milliseconds when this login must end. Null when nobody is signed in. */
export function sessionExpiresAt(): number | null {
  if (typeof window === "undefined") return null;
  const stored = localStorage.getItem(EXPIRES_KEY);
  if (stored) {
    const n = Number(stored);
    if (Number.isFinite(n) && n > 0) return n;
  }
  const refresh = localStorage.getItem("refresh_token");
  const access = localStorage.getItem("access_token");
  if (!refresh && !access) return null;
  const iat = jwtIssuedAt(refresh || access || "");
  if (iat == null) return Date.now() - 1;
  const exp = iat + SESSION_MS;
  localStorage.setItem(EXPIRES_KEY, String(exp));
  return exp;
}

export function sessionExpired(): boolean {
  const exp = sessionExpiresAt();
  return exp != null && Date.now() >= exp;
}

export function endSession() {
  if (typeof window === "undefined") return;
  for (const key of AUTH_KEYS) localStorage.removeItem(key);
  const path = window.location.pathname;
  if (
    path.startsWith("/login") ||
    path.startsWith("/signup") ||
    path.startsWith("/forgot-password") ||
    path.startsWith("/reset-password")
  )
    return;
  window.location.replace("/login");
}
