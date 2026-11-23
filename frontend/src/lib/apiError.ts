/**
 * Normalize Django REST / axios error payloads into a user-readable message.
 * Handles: detail string, detail array, field errors, nested objects, HTML 500s.
 */
export function getApiErrorMessage(
  error: unknown,
  fallback = "Something went wrong"
): string {
  if (error == null) return fallback;
  if (typeof error === "string" && error.trim()) return error.trim();

  const ax = error as {
    message?: string;
    code?: string;
    response?: {
      status?: number;
      statusText?: string;
      data?: unknown;
    };
  };

  const data = ax.response?.data;
  const status = ax.response?.status;
  if (status === 404) {
    const detail = formatErrorBody(data);
    if (detail && !/not found|no .+ matches the given query|request failed \(http 404\)/i.test(detail)) {
      return detail;
    }
    return "That record is no longer waiting. It may already have been approved, rejected, or removed. Refresh and try again.";
  }
  const fromBody = formatErrorBody(data);
  if (fromBody) return fromBody;
  if (ax.response?.status === 403) {
    return "You do not have permission to do that.";
  }
  if (ax.response?.status && ax.response.status >= 500) {
    return "The server could not complete that. If this is a duplicate code, use a different one.";
  }
  if (ax.response?.status) {
    const st = ax.response.statusText?.trim();
    return st
      ? `Request failed (${ax.response.status} ${st})`
      : `Request failed (HTTP ${ax.response.status})`;
  }

  if (ax.code === "ERR_NETWORK") {
    return "Network error — check your connection and try again";
  }
  if (typeof ax.message === "string" && ax.message && ax.message !== "Network Error") {
    return ax.message;
  }

  return fallback;
}

function formatErrorBody(data: unknown): string | null {
  if (data == null || data === "") return null;

  if (typeof data === "string") {
    const t = data.trim();
    if (!t) return null;
    // Avoid dumping HTML error pages
    if (t.startsWith("<!") || t.toLowerCase().startsWith("<html")) {
      return null;
    }
    return t.length > 600 ? `${t.slice(0, 597)}…` : t;
  }

  if (Array.isArray(data)) {
    const parts = data
      .map((x) => formatErrorBody(x) || String(x))
      .filter(Boolean);
    return parts.length ? parts.join("; ") : null;
  }

  if (typeof data !== "object") {
    return String(data);
  }

  const obj = data as Record<string, unknown>;
  const skip = new Set([
    "detail",
    "message",
    "error",
    "non_field_errors",
    "errors",
    "status_code",
  ]);

  // Field errors win over a generic detail so one message cannot hide the rest.
  const fieldParts: string[] = [];
  for (const [key, val] of Object.entries(obj)) {
    if (val == null || skip.has(key)) continue;
    if (key === "code" && typeof val === "string") continue;
    const msg = formatErrorBody(val);
    if (!msg) continue;
    const label = key.replace(/_/g, " ");
    const friendly = msg
      .replace(/This field may not be blank\.?/gi, "Enter a value.")
      .replace(/This field is required\.?/gi, "Enter a value.")
      .replace(/This field may not be null\.?/gi, "Enter a value.");
    fieldParts.push(`${label}: ${friendly}`);
  }
  if (fieldParts.length) {
    const joined = fieldParts.join(" · ");
    return joined.length > 600 ? `${joined.slice(0, 597)}…` : joined;
  }

  if ("detail" in obj) {
    const d = formatErrorBody(obj.detail);
    if (d) return d;
  }

  for (const key of ["message", "error", "non_field_errors", "errors"]) {
    if (key in obj) {
      const d = formatErrorBody(obj[key]);
      if (d) return d;
    }
  }

  return null;
}

/** Snackbar options for error toasts (longer so users can read details). */
export const errorSnackbarOpts = {
  variant: "error" as const,
  autoHideDuration: 10000,
  key: "api-error",
};
