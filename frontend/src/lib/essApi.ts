import api from "@/lib/api";

export type EssEmployee = {
  id: number;
  employee_code: string;
  first_name: string;
  last_name: string;
  full_name?: string;
  email: string;
  phone: string;
  is_attendance_free?: boolean;
  designation?: number | null;
  department?: number | null;
  department_name?: string;
  designation_title?: string;
  shift_name?: string;
  reporting_manager_name?: string | null;
  date_of_joining?: string | null;
  date_of_birth?: string | null;
  gender?: string;
  nationality?: string;
  marital_status?: string;
  national_id?: string;
  contract_type?: string;
  work_location?: string;
  status?: string;
  address?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  bank_name?: string;
  bank_iban?: string;
  photo?: string | null;
};

export type EssDashboard = {
  employee: EssEmployee;
  workplace?: {
    department: string;
    designation: string;
    location: string;
    shift: { name: string; start: string; end: string } | null;
  };
  today: {
    work_date: string;
    attendance: Record<string, unknown> | null;
    is_attendance_free: boolean;
  };
  month_attendance?: { present: number; on_time: number; late: number; absent: number };
  leave_summary?: {
    year: number;
    remaining: string;
    quota: string;
    used: string;
    balances: { name: string; remaining: string; quota: string; used: string }[];
  };
  loan?: { outstanding: string; installment: string; count: number };
  tasks?: { id: number; title: string; body: string }[];
  holidays?: { name: string; date: string }[];
  birthdays?: { name: string; department: string; day: number }[];
  counts: {
    pending_leaves: number;
    payslips: number;
    documents: number;
  };
  recent_leaves: EssLeave[];
  recent_payslips: EssPayslip[];
  recent_documents: EssDocument[];
};

export type EssLeave = {
  id: number;
  leave_type: number;
  leave_type_name?: string;
  start_date: string;
  end_date: string;
  days: string | number;
  reason: string;
  status: string;
};

export type EssPayslip = {
  id: number;
  period: number;
  period_name?: string;
  basic: string | number;
  net_pay: string | number;
  gross_pay?: string | number;
  allowances?: string | number;
  total_deductions?: string | number;
  status?: string;
  currency?: string;
  days_worked?: string | number;
};

export type EssDocument = {
  id: number;
  title: string;
  doc_type: string;
  reference?: string;
  issued_on?: string | null;
  expires_on?: string | null;
  file?: string | null;
};

export type EssAttendance = {
  id: number;
  work_date: string;
  check_in?: string | null;
  check_out?: string | null;
  status: string;
  notes?: string;
  source?: string;
  late_minutes?: number;
  worked_minutes?: number;
  worked_hours?: number;
  is_half_day?: boolean;
};

export type EssReview = {
  id: number;
  period_label: string;
  review_type: string;
  status: string;
  rating: string;
  self_rating: string;
  goals: string;
  achievements: string;
  feedback: string;
  development_plan: string;
  reviewer_name: string;
};

export type EssActivity = {
  id: number;
  created_at: string;
  event: string;
  area: string;
  outcome: string;
};

export async function fetchEssDashboard() {
  const { data } = await api.get<EssDashboard>("/ess/dashboard/");
  return data;
}

export type EssLeaveBalance = {
  id: number;
  leave_type: number;
  leave_type_name?: string;
  leave_type_code?: string;
  year: number;
  available?: string | number;
  accrued?: string | number;
  used?: string | number;
};

export async function fetchEssLeaveBalances(year?: number) {
  const { data } = await api.get<EssLeaveBalance[]>("/ess/leave-balances/", {
    params: year ? { year } : undefined,
  });
  return data;
}

export async function fetchEssLeaves() {
  const { data } = await api.get<EssLeave[]>("/ess/leaves/");
  return data;
}

function asLeaveTypes(data: unknown): { id: number; name: string; code: string }[] {
  const rows = Array.isArray(data)
    ? data
    : data && typeof data === "object" && Array.isArray((data as { results?: unknown[] }).results)
      ? (data as { results: { id: number; name: string; code: string }[] }).results
      : [];
  return rows.filter((row) => row && row.id != null);
}

export async function fetchEssLeaveTypes() {
  try {
    const { data } = await api.get("/ess/leave-types/");
    const rows = asLeaveTypes(data);
    if (rows.length) return rows;
  } catch {
    // HR catalog below still lists types an admin added.
  }
  try {
    const { data } = await api.get("/hr/leave-types/");
    return asLeaveTypes(data);
  } catch {
    return [];
  }
}

export async function submitEssLeave(payload: Record<string, unknown>) {
  const { data } = await api.post<EssLeave>("/ess/leaves/", payload);
  return data;
}

export async function fetchEssPayslips() {
  const { data } = await api.get<EssPayslip[]>("/ess/payslips/");
  return data;
}

export function essPayslipPrintUrl(id: number) {
  const base = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";
  return `${base.replace(/\/$/, "")}/ess/payslips/${id}/print/`;
}

export async function openEssPayslipPrint(id: number) {
  const token = localStorage.getItem("access_token");
  const url = `${essPayslipPrintUrl(id)}?t=${Date.now()}`;
  const res = await fetch(url, {
    cache: "no-store",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("Could not open payslip");
  const html = await res.text();
  if (!html.includes("SALARY SLIP")) {
    throw new Error("Payslip layout not available — try again after refresh");
  }
  const w = window.open("", "_blank");
  if (!w) throw new Error("Pop-up blocked — allow pop-ups for this site");
  w.document.open();
  w.document.write(html);
  w.document.close();
}

export async function fetchEssTaxCertificate() {
  const { data } = await api.get<Record<string, string>>("/ess/payslips/tax-certificate/");
  return data;
}

export async function fetchEssDocuments() {
  const { data } = await api.get<EssDocument[]>("/ess/documents/");
  return data;
}

export async function fetchEssAttendance(month?: string) {
  const { data } = await api.get<EssAttendance[]>("/ess/attendance/", {
    params: month ? { month } : undefined,
  });
  return data;
}

export async function fetchEssPerformance() {
  const { data } = await api.get<EssReview[]>("/ess/performance/");
  return data;
}

export async function patchEssPerformance(payload: {
  id: number;
  self_rating?: string;
  achievements?: string;
}) {
  const { data } = await api.patch<EssReview[]>("/ess/performance/", payload);
  return data;
}

export async function fetchEssActivity() {
  const { data } = await api.get<EssActivity[]>("/ess/activity/");
  return data;
}

export type EssTask = {
  id: number;
  title: string;
  body: string;
  status: string;
  priority: string;
  due_date: string;
  checklist: { text: string; done: boolean }[];
  assignee: number | null;
  assignee_name: string;
  created_by: number | null;
  can_remind?: boolean;
};

export async function fetchEssTasks() {
  const { data } = await api.get<EssTask[]>("/ess/tasks/");
  return data;
}

export async function createEssTask(payload: Record<string, unknown>) {
  const { data } = await api.post<EssTask>("/ess/tasks/", payload);
  return data;
}

export async function patchEssTask(payload: Record<string, unknown>) {
  const { data } = await api.patch<EssTask>("/ess/tasks/", payload);
  return data;
}

export async function remindEssTask(id: number) {
  const { data } = await api.post(`/ess/tasks/${id}/remind/`);
  return data;
}

export async function uploadEssPhoto(file: File) {
  const form = new FormData();
  form.append("photo", file);
  const { data } = await api.patch<EssEmployee>("/ess/profile/", form, {
    headers: { "Content-Type": "multipart/form-data" },
    transformRequest: [
      (body, headers) => {
        if (headers) delete headers["Content-Type"];
        return body;
      },
    ],
  });
  return data;
}

export async function essPunch(kind: "check-in" | "check-out") {
  const { data } = await api.post("/ess/attendance/punch/", { action: kind });
  return data;
}

export async function essRequestRegularization(body: {
  work_date: string;
  check_in?: string;
  check_out?: string;
  reason: string;
}) {
  const { data } = await api.post("/ess/attendance/regularize/", body);
  return data;
}

export async function essAttendanceException(notes: string) {
  const { data } = await api.post("/ess/attendance/", {
    work_date: new Date().toISOString().slice(0, 10),
    status: "exception",
    notes,
  });
  return data;
}

export async function fetchEssProfile() {
  const { data } = await api.get<EssEmployee>("/ess/profile/");
  return data;
}

export async function patchEssProfile(payload: Partial<EssEmployee>) {
  const { data } = await api.patch<EssEmployee>("/ess/profile/", payload);
  return data;
}

export type EssClaim = {
  id: number;
  claim_date: string;
  category: string;
  amount: string | number;
  status: string;
  notes?: string;
};

export async function fetchEssClaims() {
  const { data } = await api.get<EssClaim[]>("/ess/claims/");
  return data;
}

export async function submitEssClaim(payload: Record<string, unknown>) {
  const { data } = await api.post<EssClaim>("/ess/claims/", payload);
  return data;
}
